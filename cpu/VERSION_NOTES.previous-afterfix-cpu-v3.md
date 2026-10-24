# CPU package v3 notes

This is a local release candidate. Authors, license and public destination remain pending. No license grant is inferred and nothing has been submitted.

The current paper is [v5](paper/afterfix-draft-v5.md). It qualifies supplied-patch correctness, simplifies wording and adds an AI-assistance statement. All study numbers and tables are unchanged. [V4](paper/afterfix-draft-v4.md) and [v2](paper/afterfix-draft-v2.md) are historical manuscripts, not current findings.

The [historical reviewer report](paper/reviewer-report-v1.md) is preserved byte-for-byte. Its seven formerly missing targets are now included at their original paths. Its pending-review statements describe its date; the [completed internal review](review/case-review-v2.md) supersedes them. Copies under `results/paper-review-v1/` support those archival links. The canonical diagnostic inputs remain under `studies/diagnostic/`; their overlapping JSON files are byte-identical.

`tools/review_paper_cpu_diagnostics.py` is historical source provided to resolve the report's reference. It assumes the original workspace and is not the standalone reproduction entry point. Use `python -I -B reproduce.py --output rebuilt` from this package instead. That command regenerates diagnostic candidates and grades as well as the separate model studies.

For v3, `studies/v3/plan.json` records the inherited case design. `studies/v3/runtime-plan.json` supplies the actual follow-up model pins, schedule and expanded generation budgets. The original NF4 study uses its original smaller budgets.

The separate `afterfix-gpu-inference-v1.zip` supplement contains the exact frozen generation payloads, their extracted sources, checkpoint preparation code, environment records and launch instructions. It is not required for CPU replay. It does not include model weights or claim a new GPU execution. Original NF4 generation still depends on access to the recorded prepared checkpoint, which must be addressed before public release.

The CPU replay program, each study's source and raw/expected evidence, case cards, and internal review are unchanged from package v2. Original, corrected H08, v3, diagnostic and review outputs stay separate. Package v1 and v2 archives are preserved in the project.
