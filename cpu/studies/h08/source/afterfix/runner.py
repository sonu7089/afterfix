"""Model-independent public agent loop; CPU-testable without Transformers or CUDA."""
import json
import time
from .engine import materialize, public_check, run_sql
from .protocol import BUDGET, digest, parse_response, public_task, system_prompt, trace


class BudgetStop(Exception):
    pass


def feedback_message(feedback, run):
    encoded = json.dumps(feedback, separators=(',', ':'))
    if len(encoded) > BUDGET['feedback_characters']:
        # Keep a valid JSON envelope; never cut an object midway and call it complete.
        encoded = json.dumps({'truncated': True, 'original_characters': len(encoded),
                              'preview': encoded[:BUDGET['feedback_characters']//2]})
    return ('Tool result: ' + encoded + '\nBudget: ' + json.dumps({
        'turns_remaining': BUDGET['max_turns'] - len(run['turns']),
        'generated_tokens_remaining': BUDGET['max_generated_tokens_per_case'] - run['generated_tokens']}))


def run_case(task, method, generate, run, on_save=lambda: None, clock=time.monotonic, protocol=None):
    """generate(messages, max_tokens, seconds) returns text and measured token/timing fields.

    The model callback must enforce the input limit without silent truncation.
    Exceptions from generation are infrastructure errors and propagate to the controller.
    """
    if protocol is None:
        from . import protocol
    public_task, system_prompt, parse_response = protocol.public_task, protocol.system_prompt, protocol.parse_response
    begin = clock()
    view = public_task(task)
    prompt = system_prompt(method)
    run.update({'id': task['id'], 'method': method, 'turns': [], 'artifact': None,
                'artifact_turn': None, 'stop_reason': 'turn_budget', 'generated_tokens': 0,
                'status': 'running', 'public_task_sha256': digest(view),
                'system_prompt_sha256': digest(prompt)})
    messages = [{'role': 'system', 'content': prompt},
                {'role': 'user', 'content': json.dumps(view, separators=(',', ':'))}]
    on_save()
    try:
        for turn in range(BUDGET['max_turns']):
            remaining = BUDGET['case_seconds'] - (clock() - begin)
            available = BUDGET['max_generated_tokens_per_case'] - run['generated_tokens']
            if remaining < 5 or available < 24:
                run['stop_reason'] = 'time_budget' if remaining < 5 else 'token_budget'
                break
            try:
                generated = generate(messages, min(BUDGET['max_generated_tokens_per_call'], available),
                                     min(BUDGET['generation_seconds'], remaining - 2))
            except BudgetStop as exc:
                run['stop_reason'] = str(exc)
                break
            text = generated['response']
            record = {'turn': turn+1, **generated}
            run['turns'].append(record)
            run['generated_tokens'] += record['output_tokens']
            messages.append({'role': 'assistant', 'content': text})
            # Every actual generation is charged even if it crosses a wall-clock deadline.
            if clock() - begin >= BUDGET['case_seconds']:
                record['rejected_after_deadline'] = True
                run['stop_reason'] = 'time_budget'
                on_save()
                break
            ts = clock()
            try:
                action, normalization = parse_response(text, method)
                record.update(action=action['action'], normalization=normalization,
                              parsed_action=action)
            except (ValueError, TypeError) as exc:
                record['error_category'] = 'protocol'
                feedback = {'error_type': 'protocol', 'error': str(exc),
                            'instruction': 'Return exactly one complete JSON action. This turn was consumed.'}
            else:
                name = action['action']
                if name in ('test', 'submit'):
                    if view.get('condition') == 'correct_patch_given':
                        action['application_sql'] = view['application_sql']
                    run['artifact'] = {k: action[k] for k in ('application_sql', 'recovery_sql')}
                    run['artifact_turn'] = turn+1
                if name == 'submit':
                    run['stop_reason'] = 'submitted'
                    record['tool_seconds'] = clock()-ts
                    on_save()
                    break
                try:
                    if name == 'query':
                        db = materialize(view)
                        try:
                            feedback = run_sql(db, view, action['sql'], readonly=True)
                        finally:
                            db.close()
                    elif name == 'test':
                        feedback = public_check(view, action['application_sql'], action['recovery_sql'])
                        if not feedback['sql_executed']:
                            record['error_category'] = 'sql'
                    else:
                        feedback = trace(view, action['roots'], action['direction'])
                except Exception as exc:
                    record['error_category'] = 'tool'
                    feedback = {'error_type': 'tool', 'error': str(exc)}
            record['tool_seconds'] = clock()-ts
            record['feedback'] = feedback
            record['feedback_message'] = feedback_message(feedback, run)
            messages.append({'role': 'user', 'content': record['feedback_message']})
            on_save()
        run['status'] = 'completed'
    except Exception:
        run['status'] = 'infrastructure_error'
        run['stop_reason'] = 'infrastructure_error'
        raise
    finally:
        run['wall_seconds'] = clock()-begin
        on_save()
    return run
