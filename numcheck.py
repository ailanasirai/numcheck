import random
import re
from dataclasses import dataclass

UNITS = {
    "%": "%", "ev": "eV", "mev": "meV", "v": "V", "mv": "mV",
    "ma/cm2": "mA/cm2", "ma cm-2": "mA/cm2", "ma/cm²": "mA/cm2",
    "nm": "nm", "um": "um", "μm": "um", "µm": "um", "k": "K", "°c": "C",
    "ns": "ns", "us": "us", "μs": "us", "µs": "us",
    "w/m2": "W/m2", "w/m²": "W/m2", "ghz": "GHz", "mpa": "MPa", "gpa": "GPa",
}

KEYWORDS = [
    "efficiency", "bandgap", "band gap", "voltage", "current", "resistance",
    "thickness", "temperature", "lifetime", "advantage", "gain", "fill factor",
    "stability", "retention", "strength", "conductivity", "mobility",
    "loss", "limit", "capacity", "yield", "accuracy",
]

NUM = r"(?P<num>\d+(?:\.\d+)?)"
UNIT_ALT = "|".join(sorted((re.escape(u) for u in UNITS), key=len, reverse=True))
QTY_RE = re.compile(NUM + r"\s*(?P<unit>" + UNIT_ALT + r")(?![A-Za-z])", re.IGNORECASE)


@dataclass
class Qty:
    value: float
    unit: str
    keyword: str
    decimals: int
    start: int
    end: int
    raw: str


def _decimals(num_str):
    return len(num_str.split(".")[1]) if "." in num_str else 0


def extract_quantities(text, window=80):
    out = []
    low = text.lower()
    for m in QTY_RE.finditer(text):
        unit = UNITS[m.group("unit").lower()]
        s = m.start()
        ctx = low[max(0, s - window): s]
        kw, best = "", -1
        for k in KEYWORDS:
            i = ctx.rfind(k)
            if i > best:
                kw, best = k, i
        kw = kw.replace("band gap", "bandgap")
        num = m.group("num")
        out.append(Qty(float(num), unit, kw, _decimals(num), m.start(), m.end(), m.group(0)))
    return out


def values_match(a, b):
    tol = max(0.5 * 10 ** (-a.decimals), 0.003 * abs(b.value))
    return abs(a.value - b.value) <= tol + 1e-9


def check(abstract, body):
    a_qs = extract_quantities(abstract)
    b_qs = extract_quantities(body)
    flags = []
    for a in a_qs:
        same_unit = [b for b in b_qs if b.unit == a.unit]
        if any(values_match(a, b) for b in same_unit):
            continue
        same_kw = [b for b in same_unit if a.keyword and b.keyword == a.keyword]
        if same_kw:
            flags.append({
                "raw": a.raw, "keyword": a.keyword, "unit": a.unit,
                "abstract_value": a.value, "start": a.start,
                "body_values": sorted({b.value for b in same_kw})[:8],
                "reason": "abstract value not found; body has different values for the same quantity",
            })
    return flags


def perturb(value, decimals, rng):
    factor = rng.choice([0.6, 0.75, 1.25, 1.4, 1.6])
    new = round(value * factor, decimals)
    if new == value:
        new = round(value + 1, decimals)
    return new


def inject_error(abstract, body, idx, rng):
    a_qs = extract_quantities(abstract)
    q = a_qs[idx]
    b_vals = [b for b in extract_quantities(body) if b.unit == q.unit]
    for _ in range(20):
        new_val = perturb(q.value, q.decimals, rng)
        fake = Qty(new_val, q.unit, q.keyword, q.decimals, 0, 0, "")
        if not any(values_match(fake, b) for b in b_vals):
            break
    new_num = f"{new_val:.{q.decimals}f}"
    old_num = re.match(NUM, q.raw).group("num")
    new_raw = new_num + q.raw[len(old_num):]
    new_abs = abstract[:q.start] + new_raw + abstract[q.end:]
    return new_abs, {"old": q.raw, "new": new_raw, "keyword": q.keyword}


def checkable_indices(abstract, body):
    a_qs = extract_quantities(abstract)
    b_qs = extract_quantities(body)
    idxs = []
    for i, a in enumerate(a_qs):
        same_unit = [b for b in b_qs if b.unit == a.unit]
        same_kw = [b for b in same_unit if a.keyword and b.keyword == a.keyword]
        if same_kw and any(values_match(a, b) for b in same_unit):
            idxs.append(i)
    return idxs


def evaluate(papers, trials_per_paper=5, seed=0):
    rng = random.Random(seed)
    rows, tp, fn, fp = [], 0, 0, 0
    for pid, (abstract, body) in papers.items():
        fp += len(check(abstract, body))
        idxs = checkable_indices(abstract, body)
        for idx in rng.sample(idxs, min(trials_per_paper, len(idxs))):
            bad_abs, info = inject_error(abstract, body, idx, rng)
            flags = check(bad_abs, body)
            hit = any(f["raw"] == info["new"] for f in flags)
            tp += hit
            fn += (not hit)
            rows.append({"paper": pid, **info, "detected": hit})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fn": fn, "clean_flags": fp, "precision": precision,
            "recall": recall, "f1": f1}, rows


def load_arxiv(arxiv_id):
    import requests, fitz
    r = requests.get(f"https://arxiv.org/pdf/{arxiv_id}", timeout=60)
    r.raise_for_status()
    doc = fitz.open(stream=r.content, filetype="pdf")
    text = "\n".join(p.get_text() for p in doc)
    return split_abstract(text)


def split_abstract(text):
    m = re.search(r"\bintroduction\b", text, re.IGNORECASE)
    cut = m.start() if m and m.start() > 300 else min(2500, len(text) // 8)
    return text[:cut], text[cut:]
