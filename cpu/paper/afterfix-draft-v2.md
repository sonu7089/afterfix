# AfterFix: A Controlled Study of Historical Recovery from Supplied Code Patches

*Synthetic projection repair, matched Gemma 4 comparisons, and a post hoc scope-adaptation diagnostic*

## Abstract

A correct application patch need not repair previously committed state. AfterFix tests recovery-SQL generation on 24 synthetic SQLite cases with supplied patches, complete evidence and rebuildable projections. We report an original 72-attempt Gemma 4 12B NF4 study, a separate three-attempt harness correction, and a 144-attempt follow-up comparing matched 12B and 31B QAT configurations. Ordinary-tools full recovery improves from 11/24 with 12B to 18/24 with 31B within the follow-up; checklist and optional dependency traversal show no consistent benefit. However, a post hoc CPU diagnostic recovers all 24 cases by removing current-work filters from the supplied patches. The benchmark therefore measures adaptation of solution-bearing patches, not unrestricted recovery synthesis. All 132 executable follow-up artifacts are repeat-state stable, including 48 incorrect repairs; stability provides no discrimination within that subset. We present the collection as an inspectable diagnostic resource, with explicit limits on task diversity, method conclusions and production relevance.

## 1. Motivation and contribution

Deploying a correct patch may prevent future errors while leaving existing data wrong. A handler scoped to newly changed entities can be correct for future processing yet skip damaged historical records. WARP already addresses retroactive patching and legitimate later changes [1](https://dspace.mit.edu/entities/publication/b7357731-b8f9-48d9-8278-094d8925a55c), and QFix studies repair through query histories [2](https://eugenewu.net/files/papers/qfix-sigmod17.pdf). AfterFix does not introduce this problem.

We study a narrower question: when given correct application SQL and a stated recovery contract, do bounded language-model agents produce a portable repair of existing projections? We compare ordinary tools, checklist prompting and optional dependency traversal, then assess what execution and stability checks reveal about their artifacts.

The contribution is a small, auditable task collection and empirical study. A review-time diagnostic exposes a shared construction shortcut: the patches already encode sufficient reconstruction logic. This sharply limits claims of difficult recovery reasoning, while making the collection useful for examining whether agents preserve correct supplied logic and adapt its scope. We do not propose a superior recovery algorithm or claim a first benchmark for stateful agents.

For data engineers, the intended use is to inspect assumptions about authoritative evidence, permitted rewrites and recovery completeness. No production risk reduction, financial savings or engineering productivity improvement is measured.

## 2. Task contract and construction

Each case supplies a business specification, schema, records, immutable evidence, declared dependencies, writable projection tables and fixed application SQL. The host uses that patch unchanged. Every historical fixture has an empty current-work queue; all 24 cases permit full reconstruction, and none requires append-only repair. The supplied patch contains reconstruction queries restricted to current-work entities. Thus the correct-patch-given condition removes source-fix uncertainty but also supplies substantial solution information.

The 24 cases contain four instances in each of six families: delivery workflows, coupled resources, versioned storage, authorization graphs, ordered state and evidence adjudication. They instantiate acknowledgements, reservations, generations, delegation, event versions and completeness rules. These are authored miniature mechanisms, not production incident samples. Dirty states are constructed by modifying expected projections; the benchmark does not execute an original faulty application to reproduce each incident.

Agents can query the initial database, test recovery SQL on fresh copies, and submit an artifact. Public tests expose execution errors, resulting projection rows, write counts and repeat-state stability; they do not expose the expected state or private semantic verdict. Tests do not accumulate edits across turns. Full reconstruction is legal; minimal writes, uninterrupted service and external effects are not evaluated.

Python oracles compute expected projections without executing reference SQL. Before initial target-model exposure, two reference strategies per case passed all three fixture variants, and seven incorrect executable controls per case were rejected: 144 positive and 504 negative strategy/variant checks. References establish realizability, not an independently implemented recovery competitor. Authors designed both tasks and oracles; algorithmically separate implementations do not constitute independent human validation.

Seeds 0, 7 and 19 rename identifiers and vary selected numeric values within the same case structure. The identical generated artifact is replayed on all variants. These checks catch fixture-specific repairs but do not establish generalization to new schemas, incident mechanisms or deployment conditions. They are not three independent model runs. Local hashes preserve the design and artifacts; they are not external preregistration. Original development cases were excluded, while authors remained unblinded.

## 3. Outcomes and agent protocol

Full recovery requires all six checks on all variants:

| Check | Executed condition |
|---|---|
| Historical state | Repaired projections equal the Python oracle |
| Preservation | Immutable evidence and initially correct projection rows remain present |
| Repeat-state stability | A second recovery leaves the first recovery's state unchanged |
| Healthy control | Recovery leaves an already-correct fixture unchanged |
| Future patch | The supplied patch handles new evidence correctly and repeatably on a healthy fixture |
| Continuation | The supplied patch handles new evidence correctly after the generated recovery |

Preservation concerns final state, not every intermediate write: permitted delete-and-rebuild repairs can pass. Future-patch correctness is a supplied-code control, not generated-model capability. SQL errors and absent artifacts are reported separately from executable-but-wrong repairs. Visible recovery is the final artifact's complete seed-0 grade, not a successful intermediate tool call.

All methods receive the same records, evidence and declared edges. **Ordinary tools** already instruct recovery, preservation and repetition. **Checklist** reorganizes these obligations into additional reminders. **Trace access** adds traversal to the checklist: it returns existing nodes, edges and evidence references, without new private information, damaged-row localization or repair planning. Consequently, this is a test of prompt organization and optional navigation, not access to record-level provenance.

Every action and malformed response consumes one turn. No free formatting retries are allowed. Submission ends an attempt; otherwise the latest schema-valid test/submit candidate is retained, including candidates whose SQL fails. No candidate means failure. Case/method order is balanced within each model.

| Setting | Study A: original | Study B: v3 follow-up |
|---|---|---|
| Model / format | Gemma 4 12B / prepared NF4 | Gemma 4 12B and 31B / official QAT Q4_0 |
| Runtime / inference | Transformers / one T4 | llama.cpp b11836 / two T4s, full layer offload |
| Turns / total output tokens | 6 / 1,536 | 12 / 4,096 |
| Per-response output / input limit | 512 / 4,096 | 1,024 / 8,192 |
| Attempt / generation limit | 240 s / 80 s | 240 s / 80 s |
| Attempts | 72 | 144 |

Both studies use one greedy run per cell with thinking disabled. Study A compares ordinary against checklist primarily; trace access is exploratory. Its one failed batch download has no model observations; the permitted infrastructure replacement supplies that batch's cells.

Study B reuses cases after Study A outcomes were inspected. It is a separately frozen post-study comparison, not a fresh holdout. Both models share corrected SQL authorization, verified BOS transport, pinned weights, schedule and limits. Execution is serial, 31B first. The primary comparison is ordinary-tools recovery across models; remaining comparisons are secondary. Earlier startup/smoke failures contain zero benchmark attempts. No observed model failure was selectively retried.

The original and follow-up 12B runs are different configurations. Runtime, quantization, budgets and harness changes prevent attributing their score difference to one factor. Within Study B, fixed wall-clock limits interact with model speed; checkpoint differences and stage order also preclude a pure parameter-count causal claim.

## 4. Study A and separate H08 correction

| Method | Full recovery | Visible recovery | Executable but wrong |
|---|---:|---:|---:|
| Ordinary tools | 2/24 | 5/24 | 17/24 |
| Checklist | 1/24 | 7/24 | 19/24 |
| Trace access | 0/24 | 6/24 | 21/24 |

This table retains a shared H08 harness defect. The SQLite authorizer rejects a legitimate table-only read callback. All three H08 methods encounter it; checklist consumes all six turns repeating the denied read. The affected outcomes cannot be attributed solely to recovery reasoning.

After versioning the fix, we reran the complete H08 block separately: **0/1 full recovery for each method**. Ordinary and checklist submit an executable but historically incorrect repair; trace access produces a duplicate-key failure. No authorization denials remain. The original ordinary artifact still passes under the corrected grader; changed feedback causes a different rerun artifact. These three observations neither replace original cells nor create a pooled rate.

All 60 executable original artifacts are stable, including 57 wrong repairs. Of those 57, 42 already fail historical correctness visibly; 15 pass visibly but fail private variants. No trace calls occur. Study A provides bounded configuration-specific observations, not a clean H08 method comparison or evidence that historical recovery is generally beyond current models.

## 5. Study B: matched 12B and 31B

All 144 attempts complete, with no infrastructure-missing cells.

| Method | 12B full recovery | 31B full recovery | 31B minus 12B |
|---|---:|---:|---:|
| Ordinary tools | 11/24 (45.8%) | 18/24 (75.0%) | +29.2 percentage points |
| Checklist | 12/24 (50.0%) | 17/24 (70.8%) | +20.8 points |
| Trace access | 10/24 (41.7%) | 16/24 (66.7%) | +25.0 points |

Ordinary tools yield nine cases successful only for 31B, two only for 12B, nine for both and four for neither. Exclusive-success counts are eight versus three for checklist and eight versus two for trace access. The larger configuration improves aggregate results, not every case.

With ordinary tools, 31B solves all four authorization and all four evidence-adjudication cases, versus two and one for 12B. Conversely, 12B solves all four delivery cases versus three for 31B. Both remain weak on ordered-state cases: one of four for 31B, zero for ordinary-tools 12B. These family labels describe related authored cases, not independent application domains.

Within 31B, checklist loses one ordinary-tools success and adds none; trace access loses two and adds none. Within 12B, checklist adds two and loses one, while trace access adds one and loses two. 31B never calls trace; 12B calls it once. The results establish neither a consistent prompting advantage nor the effectiveness or ineffectiveness of a strategy that actually uses provenance.

Across ordinary/checklist/trace methods, visible recovery is 21/21/22 for 31B and 17/17/17 for 12B. Executable-but-wrong counts are 4/6/8 and 10/8/12. All 132 executable artifacts are stable, including those 48 wrong repairs. Stability therefore rejects none of the executable model artifacts in this study. Moreover, in both Studies A and B, every artifact passing historical correctness also passes the complete conjunction. The additional checks are useful specified safeguards, with negative-control coverage, but their incremental rejection of historically correct model artifacts is not demonstrated.

The v3 controller takes 127.68 minutes. 31B uses 33,460 output tokens and 68.92 minutes of summed attempt time; 12B uses 52,489 tokens and 49.80 minutes. Four 31B generation timeouts affect three attempts, one ending at its time budget. 12B hits a response-token cap twice and ends four attempts at the turn limit; one also exhausts total tokens. These remain outcomes under the common budgets.

## 6. Post hoc diagnostic and failure interpretation

During manuscript review, we tested whether the public patches already determine recovery. A single text transformation removes `WHERE key IN (SELECT entity FROM work)` and corresponding `AND` clauses, allowing an optional table alias. It removes two clauses per case, preserves every other predicate, and uses no case-specific branch, reference SQL or private expected state. All candidates were saved before grading with the unchanged v3 grader.

| CPU diagnostic, separate from model studies | Full recovery | Stable state |
|---|---:|---:|
| Unchanged patch used as recovery | 0/24 | 24/24 |
| No-op | 0/24 | 24/24 |
| Public-patch scope adaptation | **24/24** | 24/24 |

These counts require all three variants. The rule was chosen after inspecting the benchmark structure and model outcomes; it is not a preregistered competitor or evidence of new-task generalization. It exposes a benchmark-specific shortcut, not a generally safe SQL transformation. Removing write scopes in production can violate constraints absent here.

The diagnostic changes the interpretation: success requires adapting available solution logic, and model failures need not imply failure to infer complex business semantics. For example, 31B ordinary on H17 uses the supplied meter computation but restricts recovery to literal `east_0`. It passes the visible fixture and fails renamed variants. On H12, its deletion-only artifact removes a stale cache row without restoring the correct generation; it fails historical correctness even visibly. These are observed artifact mechanisms, not claims about the model's internal reasoning.

The no-op control also shows why stable-but-wrong behavior is not a surprising new property of idempotency. Its empirical relevance here is that public feedback and executable state stability fail to separate correct from incorrect submitted artifacts. This supports inspecting semantic outcomes, but does not establish a novel verification principle or production monitoring result.

## 7. Related work and scope

WARP [1](https://dspace.mit.edu/entities/publication/b7357731-b8f9-48d9-8278-094d8925a55c) and QFix [2](https://eugenewu.net/files/papers/qfix-sigmod17.pdf) already address historical repair and later legitimate changes. Mahif uses reenactment and slicing [3](https://arxiv.org/abs/2203.12860); Ultraverse couples application/database what-if execution [4](https://arxiv.org/abs/2211.05327v4). Castle generates cascading SQL updates [5](https://aclanthology.org/2025.emnlp-main.1700/), and Recovery-Bench evaluates agents from failed trajectories [6](https://github.com/letta-ai/recovery-bench).

The closest evaluation overlaps are substantive. ArrivalBench replays generated pipelines under changing delivery schedules [7](https://arxiv.org/abs/2610.02363); AfterFix starts from already-damaged projections with correct SQL supplied. DBA-Bench tests remediation and safety in active database deployments [8](https://arxiv.org/abs/2607.22165v2); AfterFix uses small offline copies and complete evidence. AgentTether applies dependency graphs to trajectory recovery [9](https://arxiv.org/abs/2607.06273); our traversal only navigates declared task edges. Ye and Hu use executed target/update substitutions for repair diagnosis [10](https://arxiv.org/html/2610.26650v2); our checks do not perform such causal component attribution. We claim a focused diagnostic collection, not superiority to these systems or newness of temporal, stateful or component-level evaluation.

## 8. Limitations and reproducibility

The common work-queue construction and 24/24 scope-adaptation result are central limitations. Six family labels do not remove this shared shortcut. References and author-written controls establish executability, not independent difficulty or representativeness. Independent domain review, human baselines and nontrivial automatic recovery baselines on diverse constructions are absent. Method arms overlap in instructions and information; rare trace use makes strong provenance conclusions unavailable.

One greedy run per cell does not estimate variability. Private variants preserve structure, and Study B reuses inspected cases. Small fully reconstructible projections, immutable evidence and static snapshots omit partial evidence, external effects, concurrent workloads and restricted rebuild windows. We report descriptive paired counts, not population rates, statistical significance or a causal scaling law. The original harness defect remains disclosed.

Sources, fixtures, schedules, model pins, prompts and traces are archived locally. The v3 audit reproduces all 589 feedback records and verifies 730 generation records, including two smoke calls. The CPU diagnostic is stored separately with its rule, candidate hashes and all grades. Neither it nor the manuscript revision changes sealed experiments or original scores. Public packaging and independent review remain pending; local reproducibility checks do not establish absence of every specification or implementation defect.

## References

1. Chandra et al. [Intrusion recovery for database-backed web applications (WARP)](https://dspace.mit.edu/entities/publication/b7357731-b8f9-48d9-8278-094d8925a55c). SOSP, 2011.
2. Wang, Meliou and Wu. [QFix: Diagnosing errors through query histories](https://eugenewu.net/files/papers/qfix-sigmod17.pdf). SIGMOD, 2017.
3. Campbell, Arab and Glavic. [Efficient Answering of Historical What-if Queries](https://arxiv.org/abs/2203.12860). 2022.
4. Ko et al. [Ultraverse: A System-Centric Framework for Efficient What-If Analysis for Database-Intensive Web Applications](https://arxiv.org/abs/2211.05327v4). 2025.
5. Su et al. [Castle: Causal Cascade Updates in Relational Databases with Large Language Models](https://aclanthology.org/2025.emnlp-main.1700/). EMNLP, 2025.
6. Letta. [Recovery-Bench](https://github.com/letta-ai/recovery-bench). Project repository.
7. Kothari. [ArrivalBench: Agent-Generated Data Pipelines Are Correct Once and Wrong Under Time](https://arxiv.org/abs/2610.02363). 2026.
8. Chen et al. [DBA-Bench: A Production-Fidelity Benchmark for LLM-Based Database Operations Agents](https://arxiv.org/abs/2607.22165v2). 2026.
9. Zhao et al. [AgentTether: Graph-Guided Diagnosis and Runtime Intervention for Reliable LLM Agent Operation](https://arxiv.org/abs/2607.06273). 2026.
10. Ye and Hu. [From Outcomes to Components: A Counterfactual Evaluation Framework for LLM-Proposed Repairs](https://arxiv.org/html/2610.26650v2). 2026.
