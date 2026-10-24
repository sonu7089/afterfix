# Critical review of AfterFix manuscript v1

This is an assisted internal scientific review, not external peer review or independent domain validation. It evaluates the manuscript against its saved evidence and implementation. The original manuscript and all sealed experiments remain unchanged; [manuscript v2](afterfix-draft-v2.md) is the revision.

## Overall assessment

**Major revision was warranted.** V1 was commendably explicit about negative method results, the original H08 defect and separate study protocols. However, it understated a decisive benchmark-construction limitation. A single public-patch scope transformation now passes all 24 cases. The evidence supports a controlled patch-adaptation diagnostic; it does not establish a difficult general recovery-synthesis benchmark, a new recovery algorithm or broad agent capability limits.

As a reviewer, I would not recommend v1 as a strong benchmark-novelty paper. V2 is a more defensible and transparent empirical account, but prose cannot resolve limited construction diversity, missing independent domain validation, scarce trace use or absence of a public artifact package. Acceptance or award competitiveness cannot be inferred from these revisions.

The useful aspect is an inspectable demonstration of configuration-specific agent failures even when repair logic is available, paired with explicit semantic checks. The new diagnostic strengthens the honesty and interpretability of the paper while weakening the original difficulty/novelty pitch. It should not be omitted to preserve a more impressive story.

## Major findings

### 1. Critical: the supplied patch contains a complete solution after a common scope change

All 24 tasks have empty historical `work` tables, rebuildable projections and no append-only requirement. Their supplied application patches already contain reconstruction queries. Removing their two `work` filters yields full recovery on **24/24 cases across seeds 0/7/19**. The unchanged patch and no-op each achieve **0/24**, despite both being stable on all cases.

The transformation was chosen after inspecting all public patch forms and earlier outcomes, then fixed before its private grading. It uses one rule without case-specific branches and only the archived public task list to construct candidates. All candidates were saved before private evaluation. It is a **post hoc, benchmark-specific comparator**, not a preregistered general-purpose recovery method. This is intentional solution-bearing side information under the task contract, not evidence of training contamination or unauthorized hidden-data leakage.

Evidence: [diagnostic plan](review-scope-diagnostic-plan.md), [public candidates](../results/paper-review-v1/public-candidates.json), [all diagnostic grades](../results/paper-review-v1/grades.json), [summary](../results/paper-review-v1/summary.json), [implementation](../tools/review_paper_cpu_diagnostics.py). Re-run the grading phase with `python tools/review_paper_cpu_diagnostics.py evaluate`; candidate preparation refuses to overwrite saved candidates.

**Revision:** title, abstract, task description, diagnostic table and limitations now disclose the shortcut. The paper no longer presents these results as strong evidence of difficult unconstrained recovery synthesis. No original or v3 model score is changed.

**Unresolved:** six semantic families share one decisive construction convention. A broader resource claim would require diverse task constructions where adaptation is not uniformly reducible to removing the same filters. A general rebuild baseline, meaningful partial-evidence or write-policy conditions, and independently reviewed cases would be useful in a separately scoped study. Repeating GPU runs on the current cases does not repair this limitation.

### 2. Major: the stability finding was framed too strongly

Repeat-state stability is logically insufficient for semantic correctness: a no-op is the simplest counterexample. The new no-op diagnostic makes this explicit. More importantly, **all 60 executable original artifacts and all 132 executable v3 artifacts are stable**. The wrong counts, 57 and 48, therefore show that this check discriminates none of the executable model artifacts, not that the paper discovers a new verification principle.

**Revision:** v2 gives the complete executable denominators, reports the no-op control and narrows the interpretation to the observed weakness of these feedback checks. Counts remain separate across studies. Multiple artifacts on one case are not treated as independent incident types. Model attempts with SQL errors or no artifact are not omitted from recovery denominators.

### 3. Major: incremental value of the six-component conjunction is unproven

CPU analysis of both saved studies finds **zero artifacts that pass historical correctness but fail full recovery**. Thus, the conjunctive score and historical-correctness indicator coincide on observed attempts, treating missing artifacts as failures. This does not make the other checks useless: negative controls exercise preservation and drift. It does prevent claiming that those checks independently expose additional historically correct model repairs as unsafe in these results.

Preservation also checks final immutable evidence and protected rows, not every intermediate action. All held-out cases allow rebuilding; none evaluates mandatory append-only compensation. Future-patch success is a supplied-code control. The implementation supports more policies than this evaluated case set exercises.

**Revision:** precise check definitions and this zero-incremental-rejection finding are explicit. Claims about trajectory safety, zero-write idempotency, append-only evaluation and learned patch correctness are excluded.

### 4. Major: prior-art differentiation needs a concrete task boundary

WARP, QFix, Mahif and Ultraverse preclude novelty claims for retroactive repair, history-based reconstruction or dependency-limited replay. Castle already addresses generated cascading updates. [ArrivalBench](https://arxiv.org/html/2610.02363v1) evaluates replay of generated pipelines, including temporal hazards and prompting; [DBA-Bench](https://arxiv.org/html/2607.22165v2) evaluates remediation/safety in active database workloads. These are substantive overlaps, not merely neighboring topics.

The previously unavailable [From Outcomes to Components](https://arxiv.org/html/2610.26650v2), by Hengyu Ye and Songhua Hu, was read successfully during this review. It executes target/update substitutions to diagnose repairs. Our conjunctive checks do not perform such causal component attribution. AgentTether already studies graph-guided agent recovery.

**Revision:** related work now states what AfterFix supplies and restricts relative to those tasks. The new tenth citation closes the previous retrieval gap. A focused diagnostic resource is a plausible contribution; priority, methodological superiority and broad benchmarking novelty remain unestablished. This was a targeted review, not an exhaustive systematic literature search.

### 5. Major: hard cases do not establish hard reasoning mechanisms

The v1 examples described three incident mechanisms that fail in every model/method arm. That description is true, but cannot establish why their artifacts fail. In 31B ordinary H17, the generated SQL computes the intended meter value but restricts the repair to literal `east_0`: visible recovery passes, while seeds 7 and 19 fail. In H12, the artifact deletes an obsolete row but does not insert the missing current row; a CPU replay leaves `['reuse_0', 3, 8, 1]` absent.

**Revision:** two directly inspected examples replace speculative mechanism-level reasoning claims. [Selected failure evidence](../results/paper-review-v1/selected-failures.json) stores raw artifacts, source hash, grades and visible state differences. These examples are selected illustrations, not an exhaustive failure taxonomy or causal diagnosis of internal model reasoning.

### 6. Major: method contrasts have weak treatment separation

Ordinary instructions already specify recovery, preservation and repetition. The checklist largely reorganizes them. Every arm receives the same declared edges; optional traversal adds convenience, not otherwise unavailable evidence. Zero 31B calls and one 12B call leave no convincing test of actual provenance-guided recovery. Each call costs a turn, further distinguishing optional access from a matched forced-use strategy.

**Revision:** describe prompt organization and optional navigation accurately. Preserve negative/mixed results without claiming checklist is harmful in general or provenance cannot help. Graph traversal is not promoted as a new method.

**Unresolved:** a stronger intervention requires a separately specified method and fresh evaluation scope. It cannot be inferred from the present arms or obtained by relabeling them.

### 7. Major: comparability, exposure and deployment scope

Study A's NF4/Transformers setup differs materially from Study B's QAT/llama.cpp setup and budgets. All original H08 arms encountered the authorizer bug. The corrected H08 block is a separate observation, not a clean replacement of original results. V3 fixes that boundary, but reuses inspected cases. One greedy observation, fixed 31B-first order and equal time limits do not identify a pure parameter-size effect or a scaling law.

Private variants rename IDs and alter selected values while preserving the mechanism and schema. They expose hardcoding, not new-domain transfer. Dirty state is injected into constructed projections; no original faulty program is replayed to establish incident provenance. Full public evidence, no real side effects and allowed rebuilds limit production relevance.

**Revision:** original and v3 tables remain separate, with an independent H08 block and a fourth, explicitly post hoc CPU-diagnostic block. The larger model's stronger results remain prominent. No cross-study pooled rate, significance claim or production failure estimate is introduced.

### 8. Major for publication: public reproducibility and human review remain pending

Local hashes and exact replays are strengths, but are not a public artifact package or independent verification. The current paper still needs accessible sources/data, pinned environment instructions, synthetic provenance and licenses, final author/contribution details and a recorded domain review. Existing seals are local integrity records, not preregistration.

**Revision:** public availability is not asserted. Remaining work is clearly listed rather than implied complete. No unsupported author or human-validation claim is inserted.

## What improved in v2

- Changed the title and abstract to a controlled supplied-patch study.
- Added the 24/24 scope-adaptation diagnostic, with post hoc provenance.
- Defined all six checks precisely and disclosed observed metric redundancy.
- Reported stable-artifact denominators and a no-op comparator.
- Replaced generic failure explanations with inspected 31B artifacts.
- Added the missing component-repair citation and sharper prior-art distinctions.
- Retained original, corrected H08 and v3 evidence without pooling or score edits.
- Kept the manuscript within the 3,000-word target and rechecked numerical rows.

## Decision on more computation

**No GPU work was needed for this review, and no job was launched.** The new insight came from inspecting the task construction and executing a CPU comparator. The present evidence can support a transparent, narrow diagnostic paper. A stronger general-recovery benchmark claim would require a separately planned design revision and evaluation; spending remaining GPU time on repeated old cases would not resolve the central novelty concern.
