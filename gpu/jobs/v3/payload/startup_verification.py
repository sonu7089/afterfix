"""Pinned b11836 startup evidence. Readiness alone never certifies GPU placement."""
import csv
import io
import re
import subprocess

LOG_ARGUMENTS = ['--log-verbosity', '4', '--log-colors', 'off']


def gpu_snapshot():
    result = {}
    for key, query in (
        ('devices', '--query-gpu=index,uuid,name,memory.total,memory.used'),
        ('processes', '--query-compute-apps=pid,gpu_uuid,used_gpu_memory'),
    ):
        proc = subprocess.run(['nvidia-smi', query, '--format=csv,noheader,nounits'],
                              capture_output=True, text=True, timeout=10)
        result[key] = dict(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    return result


def verify_placement(log, snapshot, server_pid, expected_layers):
    """Return explicit checks for archival, including failures, instead of discarding evidence."""
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log)
    offloads = [(int(a), int(b)) for a, b in re.findall(r'\boffloaded\s+(\d+)\s*/\s*(\d+)\s+layers to GPU\b', text)]
    buffers = {}
    for device, amount in re.findall(r'\b(CUDA\d+)\s+model buffer size\s*=\s*([0-9]+(?:\.[0-9]+)?)\s+MiB', text):
        buffers[device] = buffers.get(device, 0.0) + float(amount)
    checks = dict(full_layer_offload=bool(offloads) and all(a == b == expected_layers for a, b in offloads),
                  two_cuda_model_buffers=all(buffers.get(d, 0) > 0 for d in ('CUDA0', 'CUDA1')),
                  two_t4_devices=False, allocated_memory_on_both_devices=False)
    devices = []; processes = []; error = None
    try:
        if snapshot['devices']['returncode'] != 0:
            raise ValueError('nvidia-smi device query failed')
        for row in csv.reader(io.StringIO(snapshot['devices']['stdout']), skipinitialspace=True):
            if not row: continue
            index, uuid, name, total, used = [x.strip() for x in row]
            devices.append(dict(index=int(index), uuid=uuid, name=name, total_mib=float(total), used_mib=float(used)))
        checks['two_t4_devices'] = (len(devices) == 2 and {d['index'] for d in devices} == {0, 1}
                                    and len({d['uuid'] for d in devices}) == 2
                                    and all('T4' in d['name'] for d in devices))
        checks['allocated_memory_on_both_devices'] = len(devices) == 2 and all(d['used_mib'] > 0 for d in devices)
        # Container PID namespaces can differ from NVML's host PIDs. Record this
        # cross-check, but use explicit runtime layer/buffer evidence as the gate.
        if snapshot['processes']['returncode'] != 0:
            raise ValueError('Process telemetry unavailable; not a placement gate')
        for row in csv.reader(io.StringIO(snapshot['processes']['stdout']), skipinitialspace=True):
            if not row: continue
            pid, uuid, used = [x.strip() for x in row]
            processes.append(dict(pid=int(pid), uuid=uuid, used_mib=float(used)))
    except (KeyError, ValueError, TypeError) as exc:
        error = str(exc)
    uuids = {p['uuid'] for p in processes if p['pid'] == server_pid and p['used_mib'] > 0}
    return dict(version='afterfix-startup-v2', passed=all(checks.values()), checks=checks,
                offloaded_layers=offloads, expected_layers=expected_layers, cuda_model_buffers_mib=buffers,
                server_pid=server_pid, devices=devices, processes=processes, snapshot_parse_error=error,
                server_pid_memory_on_both_devices=bool(devices) and {d['uuid'] for d in devices}.issubset(uuids),
                failed_checks=[name for name, passed in checks.items() if not passed])
