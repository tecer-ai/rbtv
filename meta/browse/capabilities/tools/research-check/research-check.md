# research-check

`research-check` reads one research report and reports each place where it departs from the report form that [Researching with sources](../../methods/researching-with-sources.md) states. That page names the step that runs it. `research-check -h` is the interface reference.

## What a run returns

| Exit status | Standard output |
|---|---|
| 0 | `pass` |
| 1 | A first line with the count of findings, then one line per finding: `line N: <what is wrong; the correction>`, or `report: …` for a part missing from the whole report |
| 2 | Nothing; standard error says why the report could not be read |

It checks the legend line, each line under `## Sources` (the form, AT, TR and TM between 1 and 10, TS equal to their average, the average at 6 or above, a link status), each citation `[n]` against the listed sources, the `## Sources Discarded` section and the prohibited terms. It reads no web page: a score or a link status that is written in the right form passes whether or not it is true.

## Maintenance

The program is one file, `research_check.py`, on the Python 3 standard library. The legend text, the sentence for an empty discarded list, the threshold and the prohibited terms are the constants at the top of the file; they repeat what Researching with sources states, so change the page and the constants together. Run the checks with `python3 test_research_check.py` from this folder: they hold one passing report and one altered report per finding.
