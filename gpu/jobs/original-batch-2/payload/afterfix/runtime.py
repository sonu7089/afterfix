"""Process-level watchdog with a separate startup budget."""
import json
import time


def wait_worker(proc, result_path, loading_timeout=300, total_timeout=1050, poll_seconds=1,on_progress=None):
    started=time.monotonic()
    model_ready=False
    last_progress=None
    while proc.poll() is None:
        try:
            report=json.loads(result_path.read_text())
            model_ready=model_ready or report.get('status') in ('running','completed')
            runs=report.get('runs',[])
            progress=(report.get('status'),report.get('loading_phase'),len(runs),
                      runs[-1].get('generated_tokens',0) if runs else 0)
            if on_progress and progress!=last_progress:
                on_progress({'status':progress[0],'phase':progress[1],'started_cases':progress[2],
                             'latest_case_tokens':progress[3],'load_seconds':report.get('load_seconds')})
                last_progress=progress
        except (OSError,ValueError):
            pass
        elapsed=time.monotonic()-started
        reason=None
        if not model_ready and elapsed>=loading_timeout:reason='model_loading_timeout'
        elif elapsed>=total_timeout:reason='worker_total_timeout'
        if reason:
            proc.kill()
            proc.wait()
            return {'worker_returncode':proc.returncode,'worker_timed_out':True,
                    'timeout_reason':reason,'watchdog_seconds':time.monotonic()-started}
        time.sleep(poll_seconds)
    return {'worker_returncode':proc.returncode,'watchdog_seconds':time.monotonic()-started}
