# Replication files for *Are Large Language Models Method Actors?*

Liam Magee, November 2026. This standalone edition accompanies Paper 1 and its research data. The source corresponds to the paper freeze `paper1-freeze-20261119d`, commit `c7a9bb025a95e5c111bd178e3b3a1ea513d81a85`. The study data and the separate tutor software accompany the [Zenodo dataset](https://doi.org/10.5281/zenodo.24426117), version 3. The earlier data releases are [version 2](https://doi.org/10.5281/zenodo.24407172) and [version 1](https://doi.org/10.5281/zenodo.24380592).

## Reproduce the published results

Unzip the companion, enter the `machine-spirits-replication` directory, and run the following with Python 3.9 or later. The command uses the standard library and the saved study data. It runs offline, takes no API keys, and requires a new output directory.

```sh
python3 reproduce.py --out results
```

| Output in `results/` | What the command checks |
| --- | --- |
| `tables/` | All 19 tables in CSV and Markdown and their check report, 39 files in total. The program compares every byte with the frozen version. Of 678 entries, 664 are calculated from the catalogue, six are cited constants checked against their observation records, and eight are checked separately. |
| `supplementary-counts.json` | The eight other entries cover the withheld character instruction, complaints by the bored learner, and planned returns. The file also records the opening strategy counts checked against Figure 5. |
| `cited-entries.json` | All six cited entries, recalculated from the historical audit records, fidelity requests, coder comparisons and pacing readings. |
| `whole-lesson-analysis.json` | Appendix K's two coders agreed on 808 of 1,005 lessons. The recomputed JSON must match the archived JSON byte for byte. |
| `findings-9-11.csv` | Strategy-change counts for each coder and arm. The program checks 89 pairs of counts against the paper. A failed coder response is identified separately. |
| `findings-9-11-tests.csv` | The tests printed with those counts in Findings 9–11, the section on the layered tutor without the actor's texts and Appendix J, recomputed from saved coder responses: 53 entries. They are the one-sided exact sign tests on matched pairs, Fisher's exact tests between arms, the two coders' agreement and kappa, the counts by learner type and of changes of tone, and the lessons with a change in the five arms without the actor's texts. Each p-value and kappa is compared with the printed value at the printed number of decimals. |
| `findings-9-11-drama.csv` | The 19 drama-pair results printed for Findings 9–11, the section without the actor's texts, Appendix J and the Gemini rerun. Each pair was read by two reader families in both orders. A pair has a verdict only when all four readings agree. The program counts the pairs for each lesson, the ties and the pairs without a verdict from the saved readings. |
| `without-actor-texts-delivery.csv` | Replies coded as carried out with and without the actor's texts: the 752 coded replies, the fixed test on Terra's replies under a disruptive strategy, the same count for Claude Sonnet 5.5, GPT-6.1 Sol and Gemini 4 Hydrogen, the three other counts printed with p < 0.05, and the first sarcastic reply. 11 entries, with one-sided Fisher's exact tests where the paper prints one. |
| `finding-12-strategy-lines.csv` | Finding 12's table of replies carried out at saved moments under the present line and the new line, for five lines and two tutor models, each coder's count where the paper prints it, the other new wordings for humour and parable, and reverse advocacy: 26 entries. |
| `finding-12.csv` | For each of 18 final tests, the two coders' counts for both arms and the drama verdicts across 20 matched pairs. The program checks these against Figure 5. |

To render the six main-text figures and Appendix Figure J1, install librsvg so that `rsvg-convert` is on the command path. Run the following in a new output directory. The figure script uses the frozen plotting values. The verifier checks the seven SVG files byte for byte. PDF rendering can vary with the local fonts and renderer.

```sh
python3 reproduce.py --out results-with-figures --figures
```

## Check the full study data

The large data files are separate so a reader can run the checks above with a single download. For access to the complete archived requests, replies and readings, extract Zenodo parts 0 through 3 and `paper1-deposit-part4-appendix-l.zip` into one directory. Use a filesystem that supports symbolic links. `reference/archives.json` lists the 134 study directories by manuscript section. Part 4 contains the four Appendix L studies on 17 and 18 November that were listed in the manifest and omitted from parts 0–3.

With Node.js 22.12 or later installed, run the following. Replace `/path/to/unpacked-data` with the directory containing the numbered deposit folders.

```sh
python3 reproduce.py --out results-with-deposit --deposit /path/to/unpacked-data
```

The additional check reconstructs the compact observation records from the full deposit and compares them with the included copies. For the two earlier audits it uses the saved audit records in folder 35. The actor audit covered 36 folders and found actor text in 40 of 6,811 requests. The playwright audit identified 557 curly-apostrophe markers in 23,103 distinct answers. In the four Seed Bank fidelity lessons, all 65 playwright requests contained the resolved policy and zero of the 81 requests to other roles contained it. In the 409-item Qwen recoding, the counts were 22 against 6 with Qwen in place of Opus and 15 against 6 with Qwen in place of Sol. The last needed record appeared in the final tutor reply in 29 of 37 unresolved lessons. The same command compares every file in `drama-readings-9-11.zip` (2,959), `without-actor-texts-codes.zip` (2,090) and `strategy-line-codes.zip` (1,952) with the deposit, byte for byte.

## Inputs and attribution

- `data/catalogue.sql.gz` contains the part 0 SQL extract. `catalogue-notes.json` supplies two provenance notes from the reference catalogue that were absent from the SQL export and are printed in the frozen check report.
- `whole-lesson-inputs.zip` contains the inputs used by the original Appendix K analysis in deposit folder 22. `strategy-change-codes.zip` contains the saved coder responses used here for Findings 9–11. `reference/code-sources.json` identifies their study, file and digest, including failed responses.
- `cited-inputs.json.gz` records the per-study-folder actor counts, one marker flag per distinct playwright answer, one policy flag per fidelity request, coder agreement by tutor turn, and the pacing observations. `scripts/cited_counts.py` rebuilds them from the extracted deposit.
- `drama-readings-9-11.zip` contains, for each of the 17 sets of drama readings used for Findings 9–11 and the section without the actor's texts, the key that says which lesson was on which side and each reading's result and structural validation. The files have their deposit paths, in folders 24, 26, 28, 29 and 30. `reference/drama-sources.json` gives each file's digest. `reference/findings-9-11-tests.json` and `reference/findings-9-11-drama.json` list the printed values and where the paper prints them.
- `without-actor-texts-codes.zip` contains the strategy-change codes for the five arms without the actor's texts, named by study and lesson as in `strategy-change-codes.zip` (`reference/without-actor-code-sources.json` identifies their deposit file and digest), and the delivery coding keys and codes for the four tutor models at their deposit paths in folders 26 and 30 (`reference/delivery-sources.json`). `reference/without-actor-texts-delivery.json` lists the printed counts.
- `strategy-line-codes.zip` contains the coding keys and delivery codes of the four strategy-line codings in deposit folder 31, at their deposit paths (`reference/strategy-line-sources.json`). `reference/finding-12-strategy-lines.json` lists the printed counts.
- `final-tests.zip` contains the per-lesson code summaries and the pair-level or individual drama readings used for Finding 12. `selected-events.zip` contains the event fields used in the additional counts. The full events and transcripts are in the corresponding deposit folders.
- `reference/` contains the expected hashes and printed comparisons. To verify the distributed files on macOS, run `shasum -a 256 -c SHA256SUMS`. On Linux, use `sha256sum -c SHA256SUMS`.

Scripts and software use the MIT license in `LICENSE`. The research data use the attribution and CC BY 4.0 terms in `LICENSE-DATA.md`.
