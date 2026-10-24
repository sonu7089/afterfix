# NF4 companion and reproduction adapter

The local companion is `afterfix-gemma4-12b-nf4-v1`, with 21 checkpoint files, 13 weight shards and 7,710,759,449 checkpoint bytes. It was retrieved from version 1 of `nitishsongara/afterfix-checkpoint-cpu`, prepared from `google/gemma-4/transformers/gemma-4-12b-it/2`. It uses CPU bitsandbytes NF4 double quantization and FP16 compute. It is for original/H08 replications; v3 uses separate official QAT GGUF files.

Checkpoint manifest SHA-256:
`78cb8b4cc2bbfa3efe4f5ac4ff04a384e7d11d6c480b0260018f5fbdaaf3953e`

Adapter archive `afterfix-nf4-adapter-v1.zip` SHA-256:
`18b7fc71f693f2009d7cb93e97b2f9f474066098e025629ce9c940fe57777031`

The final review bundle includes the small adapter archive, checkpoint manifests, license/attribution, preparation provenance and the CPU verification report. The 7.71 GB weights remain in the separate local companion directory and are not in the CPU, GPU or final review ZIP. There is no public artifact URL yet. The proposed `nitishsongara/afterfix-gemma4-12b-nf4` name has not been registered or checked for availability.

All six historical tokenizer/configuration/provenance hashes and all 13 shard sizes match. New SHA-256 hashes cover all checkpoint files. CPU structural checks validate 2,332 tensors. The real access adapter copied and verified all files locally in 16.453 seconds; read-back hashes match. This is a CPU/SSD measurement, not a Kaggle timing prediction. Historical experiments did not record full weight hashes, so these checks cannot retrospectively prove exact historical inference bytes.

The adapter stages five original/H08 jobs and passed 26 negative controls. It changes checkpoint access and its manifest, adds helper/configuration/provenance files, and leaves prompts, cases, schedules, workers, decoding and budgets unchanged. Access/copy work stays inside the original 180-second cutoff; loading retains its 300-second cutoff. It needs about 7.71 GB of scratch space in addition to mounted weights. The adapter itself does not use private downloads; the historical controller still installs dependencies and therefore needs network access for a future run.

After extracting the adapter, a future local staging example is:

```sh
python -I -B stage_job.py --job original-batch-1 --id nitishsongara/afterfix-nf4-replication-batch-1 --checkpoint-path /kaggle/input/YOUR-ARTIFACT/checkpoint --output new-stage
```

Replace `YOUR-ARTIFACT` with an actual mounted input. This command only writes local staging files; it does not upload or execute anything. Historical notebook IDs and existing destinations are rejected. Do not replace frozen launchers in this supplement with staged launchers. Every future output belongs to a separate replication, not the paper's saved observations.

Public/cross-account access and GPU loading/generation through this adapter remain untested. A short smoke test can check them after publication is authorized. No full benchmark rerun is needed for the present analysis claims. CPU replay needs neither weights nor model access.

The companion retains upstream Apache 2.0, Google attribution and modification notices. The manuscript now uses CC BY 4.0 OR Apache 2.0. Pending manuscript-license statements in unchanged artifact/adapter v1 documents are historical and superseded by the current release scope; their file hashes remain unchanged.
