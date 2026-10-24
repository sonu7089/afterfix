# Post hoc CPU diagnostic: supplied-patch scope adaptation

This diagnostic was specified during critical review of manuscript v1, after all model outcomes and the public patch texts had been inspected. It is not preregistered, blinded, or a new held-out model evaluation. It changes no sealed cases, graders, prompts or results. It requires no GPU.

Question: does the supplied application patch already encode a complete reconstruction that can be exposed by removing the common current-work restriction?

Candidate rule, fixed before grading: for every public task, copy `application_sql` into `recovery_sql`, deleting each syntactically exact `WHERE <identifier> IN (SELECT entity FROM work)` or `AND <identifier> IN (SELECT entity FROM work)` clause. An identifier may have one alias prefix. Use case-insensitive matching, whitespace tolerance, and no case-ID-specific branches. Keep the application patch itself unchanged. Do not read private builders, reference SQL, expected state, outcome-specific hints or private seeds when constructing candidates. Construct from the archived public GPU task list and save all candidates/hashes before invoking the grader.

Controls: unchanged patch as recovery and `SELECT 1;` as a no-op. Evaluate each candidate with the unchanged v3 grader at seeds 0, 7, 19. Report every case, including SQL errors or failures. Do not revise the transformation after grading. Also inspect metric overlap in the already saved original and v3 model grades: whether any artifact passes historical correctness but fails full recovery, and whether repeat-state stability distinguishes the executable model artifacts.

This text transformation is deliberately specific to the benchmark's shared construction convention. It is not a general SQL rewrite system, deployable repair agent, safe production procedure, or evidence of new-task generalization. If successful, it reveals a benchmark shortcut / strong side information and limits the interpretation of model failure. It does not invalidate the recorded model scores or justify changing the original result tables.
