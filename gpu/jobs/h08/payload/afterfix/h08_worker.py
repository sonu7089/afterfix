"""Public-only adapter: use the frozen worker with the sealed main-study schedule."""
import json
import os
import pathlib
import sys
from . import protocol_v2


def ordered_schedule(tasks,methods,run_plan):
    if set(methods)!=set(protocol_v2.METHODS):raise ValueError('All three predeclared methods are required')
    indexed={t['id']:t for t in tasks}
    if len(indexed)!=len(tasks) or set(indexed)!={r['id'] for r in run_plan}:raise ValueError('Case roster mismatch')
    cells=[(r['id'],r['method']) for r in run_plan]
    if len(cells)!=len(set(cells)) or set(cells)!={(i,m) for i in indexed for m in methods}:raise ValueError('Incomplete or duplicate schedule')
    return [(indexed[r['id']],r['method']) for r in run_plan]


def configuration(batch):
    return {**protocol_v2.configuration(),'dataset':'afterfix-heldout-v1',
            'grading_version':'afterfix-heldout-grader-v3','development_only':False,
            'independent_families':1,'planned_cases':1,'batch':batch,
            'harness_version':'afterfix-harness-v2','evaluation_role':'H08 shared-harness correction; separate from v1',
            'note':'H08 all-method correction block; original 24-case study remains separate; private seeds are not samples.'}


def main():
    os.environ['AFTERFIX_PROTOCOL']='v2'
    from . import agent
    root=pathlib.Path(sys.argv[1]);config=json.loads((root/'run-config.json').read_text())
    # The adapter changes scheduling/metadata only. Generation, parser and runner
    # stay byte-identical to the development worker and design-frozen protocol.
    agent.active_protocol=protocol_v2
    agent.schedule=lambda tasks,methods:ordered_schedule(tasks,methods,config['schedule'])
    agent.configuration=lambda:configuration(config['batch'])
    agent.main()


if __name__=='__main__':main()
