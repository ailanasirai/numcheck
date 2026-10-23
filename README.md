# numcheck

Do the numbers in a paper's abstract actually appear in its results?

Abstracts quote headline numbers like efficiency, bandgap and voltage. I wanted
to see if a small script could catch it when an abstract number does not match
the body of the paper.

## What it does
1. Pulls every number with a unit from the abstract (%, eV, V, mA/cm2, nm, ...).
2. Attaches the nearest keyword ("efficiency", "bandgap", ...).
3. Looks for the same value in the body, with the same unit, allowing for
   rounding (14 in the abstract, 14.1 in the body is fine).
4. If the body discusses that quantity but never uses that number, it flags it.

## How I tested it
I planted wrong numbers in abstracts myself and counted how many got flagged.

- 8 arXiv papers loaded, 7 had checkable abstract numbers (18 numbers total).
- Each number was changed 20 times with a random wrong value.

| Planted error size | Caught | Recall |
|---|---|---|
| Big (25 to 60 percent off) | 360 / 360 | 1.00 |
| Small (5 to 10 percent off) | 320 / 360 | 0.89 |

![results](results.png)

The misses all came from one paper (1910.07422). Its body lists many nearby
bandgap values (1.4, 1.5, 1.6, 1.7 eV), so a wrong number often lands on
another real value and slips through. The checker is only as strict as the
paper is specific.

On unchanged abstracts the tool flagged 3 of the 18 numbers (17 percent), all in
paper 1801.02941. I read that paper by hand. The abstract's 19 percent
efficiency and two 35 percent losses are not written as numbers in the body
text. The body only gives a 75 percent combined loss and a 37 percent drop from
the 30.75 percent limit (about 19 percent), and the 35 percent values most
likely sit in Figure 6, which a text reader cannot see. I count these as false
alarms. Numbers that only live in figures get flagged.

## Limits
- Small test: 18 numbers from 7 papers.
- The errors are planted at random, not real author mistakes.
- It reads PDF text. Numbers inside figures are invisible to it, and tables are
  not parsed separately.
- The keyword is a guess from nearby words. One "95%" was labelled "bandgap".
- No LLM is used. Claims written in words are not checked.

## Run it
    pip install requests pymupdf

    from numcheck import load_arxiv, check
    abstract, body = load_arxiv("1706.08610")
    print(check(abstract, body))

The full experiment (paper loading, error planting, the figure) is in
`numcheck.ipynb`.

## Next
- Parse tables and read figures instead of flat text only.
- Add an LLM step for claims in words ("outperforms the baseline").
- Test on more papers and on real corrections from journals.

Built for the OSI Hackathon 2026. I used Claude (an AI assistant) to help write
and debug the code.
