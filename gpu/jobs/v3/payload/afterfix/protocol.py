"""Frozen protocol v1: public inputs, method prompts, parsing, and scheduling.

This module must not import case construction, reference repairs, or graders.
"""
import hashlib
import itertools
import json
import re

VERSION = 'afterfix-protocol-v1'
METHODS = ('ordinary', 'checklist', 'provenance')
BUDGET = {'max_turns': 12, 'max_generated_tokens_per_case': 4096,
          'max_generated_tokens_per_call': 1024, 'max_input_tokens': 8192,
          'case_seconds': 240, 'generation_seconds': 80,
          'feedback_characters': 7000, 'seed': 17, 'thinking': False}
PUBLIC_KEYS = ('id', 'title', 'specification', 'schema', 'application_sql',
               'writable_tables', 'immutable_tables', 'tables', 'evidence')
CHECKLIST = '''Before finishing, check these recovery obligations:
1. Establish the business grain, version/time boundary, and dependency path.
2. Correct future processing and reconstruct historical state from available evidence.
3. Preserve legitimate later activity and unrelated records.
4. Check repeated execution and behavior on an already healthy state.
5. Inspect public test results; successful execution or state stability alone does not prove correctness.
Use the checklist internally; return only an action, without a written plan.'''
BASE = '''You are repairing a synthetic SQLite application and its damaged historical projections.
Return exactly one JSON object per turn. Supported actions:
{"action":"query","sql":"SELECT ..."} reads the initial database without modifying it.
{"action":"test","application_sql":"...","recovery_sql":"..."} tests both artifacts on a fresh copy with public execution and repeatability feedback.
{"action":"submit","application_sql":"...","recovery_sql":"..."} finishes with both artifacts.
application_sql replaces the buggy application: it must process clean projections correctly and repeat safely.
recovery_sql must repair the historical state, preserve legitimate activity, repeat safely, and preserve an already healthy snapshot.
Only listed writable tables may change. No DDL, PRAGMA, ATTACH, file operations, transaction statements, or writes to immutable sources. Semicolon-separated SQLite DML is supported. Full rebuilds are allowed when the public specification permits them. Do not hardcode sample values or IDs.
All methods receive the same requirements, records, raw evidence, and declared dependency edges. Edges organize public evidence; reachability does not identify corrupt records or prove completeness of the evidence.
You have 6 turns, 1536 generated tokens total, at most 512 per response, and 240 seconds. Each query, test, trace (when available), malformed response, or submission consumes one turn. Formatting retries receive no extra budget.
Use escaped newlines inside JSON strings and no prose or Markdown. Supply exactly the fields for one supported action. SQL strings must be nonempty and at most 24000 characters.
The most recent schema-valid test or submit artifact is graded, even if SQL execution fails. A submit ends the attempt; if a budget expires, the most recent candidate is used. No candidate means failure. Hidden correctness checks are unavailable.'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


def public_task(task):
    """Allowlist inputs and derive edges only from explicit public arrow statements."""
    result = {k: task[k] for k in PUBLIC_KEYS}
    # Copy nested records too: no caller can mutate the shared task through a view.
    result = json.loads(json.dumps(result))
    edges = []
    tables = set(result['tables'])

    def node(label):
        matches = [t for t in sorted(tables) if re.search(r'\b' + re.escape(t) + r'\b', label)]
        return matches[0] if len(matches) == 1 else label

    for index, fact in enumerate(result['evidence'], 1):
        for statement in fact.split(';'):
            parts = [p.strip() for p in statement.split('->')]
            for left, right in zip(parts, parts[1:]):
                for source in left.split('+'):
                    for target in right.split('+'):
                        source, target = source.strip(), target.strip()
                        if not source or not target:
                            raise ValueError('Empty declared dependency endpoint')
                        edges.append({'source': node(source), 'target': node(target),
                                      'source_label': source, 'target_label': target,
                                      'evidence_id': f'e{index}'})
    result['declared_dependencies'] = edges
    return result


def system_prompt(method):
    if method not in METHODS:
        raise ValueError('Unknown method')
    text = BASE
    if method != 'ordinary':
        text += '\n' + CHECKLIST
    if method == 'provenance':
        text += '''\nAdditional action:
{"action":"trace","roots":["table_or_declared_node"],"direction":"upstream"}
direction is upstream or downstream. It traverses only the supplied declared dependency edges, returning reached nodes, edges, and their original evidence references. Trace does not query hidden state, infer missing edges, select damaged rows, generate repair SQL, or validate correctness. It consumes a normal turn. Use it when dependency organization helps.'''
    return text


def parse_response(text, method, recovery_only=False):
    """Lossless wrappers/JSON whitespace normalization, never SQL repair or object selection."""
    if method not in METHODS:
        raise ValueError('Unknown method')
    normalized = []
    text = text.strip()
    # The observed model sometimes emits this exact channel-like marker as text.
    if text.startswith('thought\n') or text.startswith('thought\r\n'):
        text = text.split('\n', 1)[1].strip()
        normalized.append('leading_thought_marker')
    match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text, flags=re.DOTALL)
    if match:
        text = match.group(1).strip()
        normalized.append('single_markdown_fence')
    out, quoted, escaped = [], False, False
    for char in text:
        if quoted and not escaped and char in '\n\r\t':
            out.append({'\n': r'\n', '\r': r'\r', '\t': r'\t'}[char])
            if 'json_string_whitespace' not in normalized:
                normalized.append('json_string_whitespace')
            continue
        out.append(char)
        if escaped:
            escaped = False
        elif char == '\\' and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key')
            value[key] = item
        return value

    def invalid_constant(value):
        raise ValueError('Nonstandard JSON constant')

    action = json.loads(''.join(out), object_pairs_hook=unique, parse_constant=invalid_constant)
    if not isinstance(action, dict):
        raise ValueError('Expected exactly one JSON object')
    name = action.get('action')
    fields = {'query': {'action', 'sql'},
              'test': {'action', 'application_sql', 'recovery_sql'},
              'submit': {'action', 'application_sql', 'recovery_sql'}}
    if recovery_only:
        fields['test'].remove('application_sql')
        fields['submit'].remove('application_sql')
    if method == 'provenance':
        fields['trace'] = {'action', 'roots', 'direction'}
    if not isinstance(name, str) or name not in fields or set(action) != fields[name]:
        raise ValueError('Unsupported action or unexpected/missing fields')
    for key in ('sql', 'application_sql', 'recovery_sql'):
        if key in action and (not isinstance(action[key], str) or not action[key].strip()
                              or len(action[key]) > 24000):
            raise ValueError('SQL must be a nonempty string of at most 24000 characters')
    if name == 'trace':
        roots = action['roots']
        if (not isinstance(roots, list) or not 1 <= len(roots) <= 16
                or any(not isinstance(r, str) or not r for r in roots)
                or len(set(roots)) != len(roots)
                or action['direction'] not in ('upstream', 'downstream')):
            raise ValueError('Trace needs 1-16 distinct roots and upstream/downstream direction')
    return action, normalized


def trace(task, roots, direction):
    edges = task['declared_dependencies']
    nodes = set(task['tables']) | {e[k] for e in edges for k in ('source', 'target')}
    if direction not in ('upstream', 'downstream') or not set(roots) <= nodes:
        raise ValueError('Unknown trace root or direction')
    reached = set(roots)
    source, target = ('target', 'source') if direction == 'upstream' else ('source', 'target')
    changed = True
    while changed:
        before = len(reached)
        reached.update(e[target] for e in edges if e[source] in reached)
        changed = len(reached) != before
    selected = [e for e in edges if e[source] in reached and e[target] in reached]
    ids = sorted({e['evidence_id'] for e in selected}, key=lambda x: int(x[1:]))
    return {'roots': roots, 'direction': direction, 'nodes': sorted(reached), 'edges': selected,
            'evidence': {i: task['evidence'][int(i[1:])-1] for i in ids},
            'note': 'Declared dependencies only; reachable does not mean damaged. Missing edges are not inferred.'}


def schedule(tasks, methods):
    """Six permutations balance positions and ordered method pairs over six task blocks."""
    if not methods or len(set(methods)) != len(methods) or not set(methods) <= set(METHODS):
        raise ValueError('Select distinct known methods')
    if len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError('Duplicate task IDs')
    order = tuple(m for m in METHODS if m in methods)
    permutations = list(itertools.permutations(order))
    return [(task, method) for i, task in enumerate(tasks) for method in permutations[i % len(permutations)]]


def configuration():
    return {'protocol': VERSION, **BUDGET, 'decoding': 'greedy',
            'artifact_selection': 'latest_schema_valid_test_or_submit_including_failed_execution',
            'methods': {m: {'prompt_sha256': digest(system_prompt(m))} for m in METHODS}}


def limits(attempts):
    if not isinstance(attempts, int) or attempts < 1:
        raise ValueError('At least one attempt is required')
    worker = 300 + attempts * (BUDGET['case_seconds'] + 15) + 60
    return {'worker_timeout_seconds': worker, 'model_loading_timeout_seconds': 300,
            'notebook_timeout_seconds': worker + 360}
