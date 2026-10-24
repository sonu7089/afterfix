"""Versioned correct-patch-given development protocol. No private imports."""
from . import protocol as v1
from .protocol import BUDGET, METHODS, digest, limits, schedule, trace

VERSION='afterfix-deep-protocol-v1'
BASE='''You are recovering historical data in a synthetic SQLite application AFTER a verified correct code patch.
application_sql in the task is fixed and already correct. The host always uses it unchanged. Return recovery SQL only.
Return exactly one JSON object per turn. Supported actions:
{"action":"query","sql":"SELECT ..."} reads the initial database without modifying it.
{"action":"test","recovery_sql":"..."} tests recovery then the fixed patch on a fresh copy, with public execution and repeatability feedback.
{"action":"submit","recovery_sql":"..."} finishes with the recovery artifact.
Recovery must restore the specified historical state, preserve legitimate later activity, repeat safely and preserve an already healthy state.
Only listed writable tables may change. append_only_tables allows new INSERTs only: UPDATE, DELETE and REPLACE of existing rows are blocked, even if followed by reinsertion. Other writable tables may be rebuilt when the specification permits it.
No DDL, PRAGMA, ATTACH, filesystem operations, transaction statements or writes to immutable sources. Semicolon-separated SQLite DML is supported. Do not hardcode sample values or IDs.
All methods receive identical requirements, records, raw evidence and declared dependency edges. Edges organize public evidence; reachability does not identify corrupt records or prove evidence completeness.
You have 12 turns, 4096 generated tokens total, at most 1024 per response, and 240 seconds. Every query, test, trace (when available), malformed response or submission consumes one turn. No extra formatting retries.
Use escaped newlines in JSON strings and no prose or Markdown. Supply exactly the fields for one action. SQL strings must be nonempty and at most 24000 characters.
The latest schema-valid test or submit recovery is graded even if its SQL fails. A submit ends the attempt; on budget expiry the latest candidate is used. No candidate means failure. Hidden correctness checks are unavailable.'''


def public_task(task):
    result=v1.public_task(task)
    for key in ('append_only_tables','condition','family','history_variant'):
        # Copy metadata through JSON to preserve the public view isolation boundary.
        import json
        result[key]=json.loads(json.dumps(task[key]))
    return result


def system_prompt(method):
    if method not in METHODS:
        raise ValueError('Unknown method')
    result=BASE
    if method!='ordinary':
        result+='\n'+v1.CHECKLIST.replace('Correct future processing and reconstruct historical state from available evidence.',
                                          'Use the verified patch unchanged and reconstruct historical state from available evidence.')
    if method=='provenance':
        result+='\nAdditional action:\n{"action":"trace","roots":["table_or_declared_node"],"direction":"upstream"}\nDirection is upstream or downstream. It traverses only supplied declared dependency edges and returns reached nodes, edges and original evidence references. It cannot inspect hidden state, infer missing edges, select damaged rows, generate repairs or validate correctness. It consumes a normal turn.'
    return result


def parse_response(text,method):
    return v1.parse_response(text,method,recovery_only=True)


def configuration():
    return {**v1.configuration(),'protocol':VERSION,'condition':'correct_patch_given',
            'grading_version':'afterfix-heldout-grader-v3',
            'methods':{m:{'prompt_sha256':digest(system_prompt(m))} for m in METHODS},
            'development_only':False,'independent_families':6,'post_study_followup':True,
            'note':'Post-study follow-up on the same 24 synthetic cases; separate from original evaluation; seeds are robustness checks.'}
