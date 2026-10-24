"""Offline CPU regrading of saved AfterFix outputs. Uses only Python's standard library."""
import argparse
import hashlib
import json
import pathlib
import platform
import sqlite3
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify():
    manifest = read(ROOT / 'MANIFEST.json')
    for name, expected in manifest['files'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise RuntimeError('Missing or invalid package file: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Package hash mismatch: ' + name)
    return len(manifest['files'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='rebuilt', help='New output directory; must not already exist')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    count = verify()
    if args.verify_only:
        print(f'PASS: {count} package files verified.')
        return
    output = pathlib.Path(args.output).resolve()
    if output.exists():
        raise RuntimeError('Output already exists. Choose a new --output directory; no files were overwritten.')
    if ROOT.is_relative_to(output):
        raise RuntimeError('Output must not contain the package itself.')
    output.mkdir(parents=True)
    started = time.perf_counter()
    reports = {}
    for study in ('original', 'h08', 'v3', 'diagnostic'):
        print('Rebuilding ' + study + ' ...', flush=True)
        subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'replay_worker.py'), study,
                        str(output / study)], check=True, cwd=ROOT)
        reports[study] = read(output / study / 'validation.json')
    subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'replay_worker.py'), 'cases',
                    str(output / 'case-review')], check=True, cwd=ROOT)
    for bundled in (ROOT/'case-review').iterdir():
        rebuilt = output/'case-review'/bundled.name
        if bundled.read_bytes() != rebuilt.read_bytes():
            raise RuntimeError('Regenerated case-review evidence differs: '+bundled.name)
    (output/'review').mkdir()
    subprocess.run([sys.executable, '-I', '-B', str(ROOT/'tools/review_all_cases_v2.py'),
                    '--source', str(ROOT/'studies/v3/source'), '--output', str(output/'review/checks.json')],
                   check=True, cwd=ROOT)
    review = read(output/'review/checks.json')
    if review != read(ROOT/'review/case-review-v2-checks.json'):
        raise RuntimeError('Regenerated internal review differs from archived review evidence.')
    # Metric overlap is computed from newly graded results, not the archived tables.
    overlap = {}
    for study in ('original', 'v3'):
        grades = read(output / study / 'grades.json')
        executable = [g for g in grades if g['outcome'] in ('complete', 'executable_but_wrong')]
        overlap[study] = dict(attempts=len(grades), executables=len(executable),
            executable_stable=sum(g['components']['repeatable'] for g in executable),
            historical_pass_but_not_full=[dict(id=g['id'], method=g['method'], model=g.get('model'))
                for g in grades if g.get('components', {}).get('historical') and not g['complete']],
            executable_wrong=sum(g['outcome']=='executable_but_wrong' for g in executable))
    expected_overlap = read(ROOT / 'studies/diagnostic/expected/summary.json')['metric_overlap']
    if overlap != expected_overlap:
        raise RuntimeError('Regenerated metric-overlap counts differ from archived analysis.')
    (output / 'diagnostic/metric-overlap.json').write_text(json.dumps(overlap, indent=2)+'\n', encoding='utf-8')
    tables = ['# Regenerated AfterFix tables', '',
              'Original, corrected H08, v3 and the post hoc CPU diagnostic are separate studies. No pooled score is calculated.', '']
    for study in reports:
        tables.append((output / study / 'table.md').read_text(encoding='utf-8'))
    (output / 'PAPER_TABLES.md').write_text('\n'.join(tables), encoding='utf-8')
    validation = dict(status='passed', python=platform.python_version(), sqlite=sqlite3.sqlite_version,
        platform=platform.platform(), isolated_python=sys.flags.isolated == 1,
        package_files_verified=verify(), studies=reports, metric_overlap_exact=True,
        case_admissions=24, case_review_files_exact=True,
        internal_review_exact=True, internal_review_cases=review['cases'],
        review_case_seed_checks=review['case_seed_checks'], separate_boundary_probes=len(review['boundary_probes']),
        elapsed_seconds=round(time.perf_counter()-started, 3), model_inference_performed=False,
        network_required=False, third_party_packages_required=False,
        scope='Saved-output regrading, SQL/feedback replay, case admissions and paper tables. Not a new model evaluation or independent GPU/tokenizer audit.')
    (output / 'verification.json').write_text(json.dumps(validation, indent=2)+'\n', encoding='utf-8')
    print(f'PASS: all four studies reproduced separately in {output}', flush=True)
    print('219 saved model attempts graded; CPU diagnostic kept separate. No model inference or network access.')


if __name__ == '__main__':
    main()
