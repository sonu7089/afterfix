# AfterFix

**Nitish Songara, Independent researcher**

AfterFix evaluates how agents adapt supplied SQL patches to repair existing data in 24 synthetic SQLite cases. Its contribution is an inspectable task collection and controlled evaluation with explicit evidence authority, permitted changes and executable recovery criteria. It does not establish a new recovery algorithm, production benefits or prompting superiority. A post hoc filter-removal diagnostic solves all 24 cases and limits claims of difficulty and generality.

## Paper and reproduction

- [Paper](paper/afterfix-publication-v8.md), 2,942 words, and [seven-page PDF](paper/afterfix-paper-v1.pdf).
- [Public CPU notebook](https://www.kaggle.com/code/nitishsongara/afterfix-study-reproduction).
- [CPU dataset](https://www.kaggle.com/datasets/nitishsongara/afterfix-cpu-reproduction).
- [CPU package v6](archives/afterfix-cpu-v6.zip) and [checksum](archives/afterfix-cpu-v6.zip.sha256).
- [Frozen GPU inference supplement](gpu/README.md) and [archive](archives/afterfix-gpu-inference-v3.zip).
- [NF4 companion and adapter](NF4_PUBLIC_ACCESS.md).
- [Current publication status](RELEASE_STATUS.md) and [Writeup handoff](WRITEUP_HANDOFF.md).

Use Python 3.12 or newer with standard sqlite3, no external packages and a new output directory:

```sh
python -I -B cpu/reproduce.py --output rebuilt
```

This regrades 219 saved model attempts, exactly replays 941 feedback records, and reproduces the separate diagnostic and internal case review. It does not generate model responses or remeasure GPU timings. Input hashes remain byte-exact. V6 permits only CRLF/LF differences in regenerated case-review documents, after the first public Linux run exposed that portability issue. [Portability notes](cpu/VERSION_NOTES.md) and [local verification](verification/cpu-portability.json) retain the details. Earlier archives remain unchanged.

## Separate results

| Evidence | Full recovery: ordinary / checklist / trace access |
|---|---|
| Original 12B NF4, 72 attempts | 2/24, 1/24, 0/24 |
| Corrected H08, 3 separate attempts | 0/1, 0/1, 0/1 |
| Matched v3 31B, 72 attempts | 18/24, 17/24, 16/24 |
| Matched v3 12B, 72 attempts | 11/24, 12/24, 10/24 |
| Post hoc CPU diagnostic | Scope adaptation 24/24; patch-only and no-op 0/24 |

The original H08 harness bug remains disclosed. Corrected H08 does not replace original cells. V3 uses different budgets and runtime from the original, reuses inspected cases and runs 31B first. The observed model difference does not isolate parameter count causally. The post hoc diagnostic and AI-assisted internal review are separate from model observations; the review is not independent domain validation.

## Licenses and provenance

Original code and synthetic benchmark: [Apache 2.0](LICENSE). Original publication manuscript v8 and PDF: **CC BY 4.0 OR Apache 2.0**, at the recipient's choice. See [license scope](LICENSE_SCOPE.md), [CC BY text](LICENSE-CC-BY-4.0) and [NOTICE](NOTICE). The NF4 model retains its upstream license and Google attribution. Font programs and other third-party material retain their own terms.

Historical review documents and archives retain their original metadata, including earlier pending-publication statements. Current root metadata supersedes those administrative statements without changing evidence. [CITATION.cff](CITATION.cff) identifies this software and benchmark release. No funding was received; Nitish Songara is the sole author. AI assistance is disclosed in the paper.

Publication of these artifacts is not a competition submission. The author is handling the Kaggle Writeup separately.
