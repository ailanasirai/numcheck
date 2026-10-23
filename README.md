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

On unchanged abstracts the tool raised 3 flags, all in paper 1801.02941. I have
not yet checked by hand whether those are real mismatches or PDF parsing
mistakes, so I do not count them as findings.

## Limits
- Small test: 18 numbers from 7 papers.
- The errors are planted at random, not real author mistakes.
- It reads PDF text. Tables are not parsed separately and odd formatting can
  confuse it.
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
- Parse tables properly instead of reading flat text.
- Add an LLM step for claims in words ("outperforms the baseline").
- Test on more papers and on real corrections from journals.

Built for the OSI Hackathon 2026. I used Claude (an AI assistant) to help write
and debug the code.
