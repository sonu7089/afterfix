# Short AfterFix case-review checklist

Reviewer: __________  Date: __________  Case ID: __________

Open [the 24 case cards](case-review/INDEX.md), or run the CPU command in README.md
and open `rebuilt/case-review/INDEX.md` to annotate freshly generated copies.
Review all 24 cases before describing the benchmark as domain reviewed. The cards
contain answers that were hidden from the evaluated models. All 24 cases have completed internal AI-assisted review; independent human validation remains absent. See [review decisions](review/case-review-v2.md). Historical specifications are retained verbatim and qualifications appear separately.

For each case, check:

- [ ] **Authority:** Which immutable records determine truth? Are precedence,
  event order, versions, cancellations and conflicting evidence unambiguous?
- [ ] **Expected state:** Hand-check affected rows and at least one unrelated row.
  Record the expected value and why it follows from the business rule.
- [ ] **Preservation:** Are legitimate later actions retained? Is any stale state
  mistaken for an action that should be preserved?
- [ ] **Recovery contract:** Is full rebuilding realistic under the stated scope?
  All current cases allow it, begin with an empty work queue, and impose no
  append-only constraint. Record where production would require stronger rules.
- [ ] **Grader checks:** Inspect healthy-state behavior, repeat execution and new
  evidence after recovery. Check that negative controls fail for the right reason.
  Seeds 7 and 19 are variants, not new independent cases.
- [ ] **Decision:** Mark accepted, accepted with a stated limitation, or defect
  found. Give a concrete row-level example for every defect or disagreement.

Priority cases for any further independent review: H08 (corrected query authorizer), H12 (identifier reuse and
versioning), H17 (a visible-only success with a hard-coded identifier), then one
case from each remaining family. Complete the rest before claiming full review.

Record decisions here or in the generated cards:

| Case IDs | Initial status | Reviewer / decision / evidence |
|---|---|---|
| H01, H02, H03, H04 | Internal AI review complete | See review log |
| H05, H06, H07, H08 | Internal AI review complete | See review log |
| H09, H10, H11, H12 | Internal AI review complete | See review log |
| H13, H14, H15, H16 | Internal AI review complete | See review log |
| H17, H18, H19, H20 | Internal AI review complete | See review log |
| H21, H22, H23, H24 | Internal AI review complete | See review log |

Do not edit sealed fixtures, replace scores or silently exclude difficult cases.
If review finds a defect, preserve this package and document a separately versioned
correction with its effect on each study. A real defect can justify more evaluation;
unused GPU quota alone does not.
