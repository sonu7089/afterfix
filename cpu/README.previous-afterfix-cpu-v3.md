# AfterFix offline CPU reproduction package v3

Local release candidate prepared on 24 October 2026. No GPU, model weights, API key,
Kaggle account, network connection or third-party Python package is needed.

## Run

Use Python 3.12 or newer with its standard sqlite3 module. From this extracted folder:

```sh
python -I -B reproduce.py --output rebuilt
```

Use `py -3` instead of `python` if that is your Windows launcher. The output folder
must be new. The command verifies package hashes before and after execution and
fails if any score or replay differs. It does not overwrite archived evidence.
For an integrity-only check, run `python -I -B reproduce.py --verify-only`.
The delivered verification report records the actual tested Python and SQLite
versions. Other versions can change SQLite error strings and fail exact replay.
Treat a mismatch as something to investigate, not permission to replace evidence.

## What is reproduced

The script regrades 219 saved model attempts from their generated SQL, using the
exact archived source version for each study in a separate Python process. It
checks the schedule, public-task and system-prompt hashes, action parsing, artifact
selection and recorded token accounting. Every non-submission tool or protocol
feedback record is rebuilt and compared with the saved feedback and its envelope.
It also rebuilds the post hoc candidates from public patches, checks their 72
case/rule grades, reruns the 24-case admission suite, and generates review cards.

The raw outputs and archived grades are separate inputs. Regenerated grades must
match every archived grade field, not just the reported totals. Summary tables,
family results, paired contrasts and metric overlap are derived from the new
grades. No pooled success rate is produced.

This is reproduction of scoring and analysis from saved model outputs. Model
generation, native GPU transport, tokenizer token counts, GPU placement and GPU
timings are not independently rerun. Recorded resource data remains historical.
Archived validation records document the earlier GPU audits. This compact package
does not contain the full native stream logs, weights, download code or every file
referenced by historical seals. See `provenance/source-map.json` for exact copied
paths and hashes and `provenance/build-integrity.json` for the full workspace seal
check performed at packaging. `MANIFEST.json` covers the actual package contents.

## Keep these four studies separate

| Folder | Observations | Full recoveries: ordinary / checklist / trace access |
|---|---:|---|
| studies/original | 72 saved 12B NF4 attempts | 2/24, 1/24, 0/24 |
| studies/h08 | 3 corrected H08 attempts | 0/1, 0/1, 0/1 |
| studies/v3 | 144 saved QAT attempts | 31B: 18/24, 17/24, 16/24; 12B: 11/24, 12/24, 10/24 |
| studies/diagnostic | 24 cases, 3 deterministic rules, no model attempts | Scope adaptation 24/24; patch only 0/24; no-op 0/24 |

The original uses the original harness, including its H08 query-authorizer bug.
Corrected H08 scores do not replace original cells. The original batch 3 startup
failure had zero attempts; the permitted retry supplies its 18 observations once.
Deep v1/v2 failed before benchmark generation and do not contribute model scores.
They remain infrastructure history, not failed recoveries.

The v3 study uses a corrected harness and different runtime and budgets from the
original. The 31B and 12B v3 methods share that protocol, but the cases had already
been inspected and 31B ran first. Do not attribute the difference solely to model
size or call this a new holdout. Trace access is the saved `provenance` method key.
No checklist or trace advantage is established.

The post hoc scope rule was chosen after inspecting tasks and model outcomes.
It removes current-work filters from the supplied patch. It is a diagnostic
of construction regularity, not a preregistered competing agent or novel recovery
algorithm. All 24 cases allow full rebuilding and have no append-only constraint.
The small synthetic SQLite fixtures do not measure production cost or scalability.

## Grading details

Each case uses fixture seeds 0, 7 and 19; these are variants, not independent
observations. Full recovery requires every component on every variant: historical
state correctness, preservation, repeatability, healthy-state safety, future
behavior under the supplied fixed patch, and continuation from the recovered state.
The application patch is given and cannot be changed. Python oracles compute
expected projections. The exact executable definitions are in each study's
`source/afterfix/heldout_grade.py` and `heldout_cases.py`/`heldout_remaining.py`.

All executable saved repairs were stable, including many wrong repairs. Historical
correctness and full recovery coincide in these observed model runs. Do not claim
that the other grading components independently rejected additional model repairs.

The review audit can also be rerun independently:

```sh
python -I -B tools/review_all_cases_v2.py --source studies/v3/source --output review-rebuilt.json
```

The main reproduction command performs this check automatically and compares its output with the archived review. It preserves the four study folders and puts review outputs in a separate `review/` folder.

## Read the outputs

- `rebuilt/PAPER_TABLES.md`: separate study tables.
- `rebuilt/<study>/grades.json`: newly computed grades.
- `rebuilt/<study>/summary.json`: computed method and family results.
- `rebuilt/original/analysis.json` and `rebuilt/v3/analysis.json`: exact regenerated
  family, component and paired-method analyses checked against archived summaries.
- `rebuilt/<model study>/case-results.csv`: one row per scheduled attempt.
- `rebuilt/<model study>/feedback-replays.json`: exact feedback checks.
- `rebuilt/<model study>/recorded-resources.json`: saved runtime/token accounting.
- `rebuilt/v3/paired-model-comparison.json`: case-level paired model outcomes.
- `rebuilt/diagnostic/metric-overlap.json`: checks on metric redundancy.
- `rebuilt/verification.json`: verification status and environment.
- `rebuilt/case-review/INDEX.md`: 24 review cards and admission-check results.

Consult the completed internal review in `review/case-review-v2.md`. It documents H04/H12 tie gaps, H23 empty-stream behavior, H24 work expansion and H19 reset wording. Separate probes are not model observations.

For further review, use [the short checklist](CASE_REVIEW_CHECKLIST.md). Prebuilt
[case cards](case-review/INDEX.md) are included for convenience and regenerated
independently by the CPU command. Leave these packaged copies unchanged; record
review decisions in the regenerated copies or a separate review log.
The current manuscript is [paper v5](paper/afterfix-draft-v5.md). V4 and the historical reviewer report remain unchanged. All seven historical report links now resolve to included copies. See [version and navigation notes](VERSION_NOTES.md).
See [release status](RELEASE_STATUS.md) before distributing the archive.
