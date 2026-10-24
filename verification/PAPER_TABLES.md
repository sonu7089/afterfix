# Regenerated AfterFix tables

Original, corrected H08, v3 and the post hoc CPU diagnostic are separate studies. No pooled score is calculated.

## Original 12B NF4 study

Original harness, including the H08 query-authorizer bug. Corrected H08 is separate.

| Model / method | Full recovery | Visible | Executable but wrong |
|---|---:|---:|---:|
| 12b_nf4 / Ordinary tools | 2/24 | 5/24 | 17/24 |
| 12b_nf4 / Checklist | 1/24 | 7/24 | 19/24 |
| 12b_nf4 / Trace access | 0/24 | 6/24 | 21/24 |

## Corrected H08 study

Three new attempts under harness v2. No replacement of original cells.

| Model / method | Full recovery | Visible | Executable but wrong |
|---|---:|---:|---:|
| 12b_nf4 / Ordinary tools | 0/1 | 0/1 | 1/1 |
| 12b_nf4 / Checklist | 0/1 | 0/1 | 1/1 |
| 12b_nf4 / Trace access | 0/1 | 0/1 | 0/1 |

## Matched v3 model comparison

Reused cases, expanded protocol, QAT runtime, 31B first. Separate from original NF4.

| Model / method | Full recovery | Visible | Executable but wrong |
|---|---:|---:|---:|
| 31b / Ordinary tools | 18/24 | 21/24 | 4/24 |
| 31b / Checklist | 17/24 | 21/24 | 6/24 |
| 31b / Trace access | 16/24 | 22/24 | 8/24 |
| 12b / Ordinary tools | 11/24 | 17/24 | 10/24 |
| 12b / Checklist | 12/24 | 17/24 | 8/24 |
| 12b / Trace access | 10/24 | 17/24 | 12/24 |

## Post hoc CPU diagnostic

Chosen after inspecting tasks and model outcomes. Not pooled with model runs.

| Rule | Full recovery | Stable |
|---|---:|---:|
| scope_adaptation | 24/24 | 24/24 |
| patch_only | 0/24 | 24/24 |
| no_op | 0/24 | 24/24 |
