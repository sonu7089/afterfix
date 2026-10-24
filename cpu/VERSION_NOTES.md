# CPU package v6: portable document comparison

The first public Kaggle CPU run reproduced all 219 model grades, 941 feedback records and diagnostic grades, then failed the generated case-review document comparison. Archived documents use Windows CRLF; Linux generated LF. Retrieved examples have identical text.

V6 changes only that document comparison to treat CRLF and LF equally. Every other byte must match. It reports both byte equality and normalized text equality explicitly. Input manifest verification remains byte-exact, including original archived case cards. All source graders, raw responses, expected grades, cases, prompts, oracles and frozen inference payloads are unchanged. V5 and the failed cloud run remain available.

Run `python -I -B reproduce.py --output rebuilt` in a new output directory. Original, corrected H08, matched v3 and post hoc diagnostic outputs remain separate. This is CPU saved-output replay, not model inference.

Publication was authorized by the author. Historical local-review and pending-release notices are preserved inside versioned records. The public repository's current metadata supersedes those administrative statements; no historical data is replaced.
