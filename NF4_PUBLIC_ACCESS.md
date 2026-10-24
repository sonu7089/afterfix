# NF4 public access

The separate 7.71 GB companion is being uploaded to Kaggle. Do not assume the target is downloadable until publication verification is recorded here. No weight files are in this Git repository.

Artifact identity: `afterfix-gemma4-12b-nf4-v1`, 21 checkpoint files, 13 weight shards, 7,710,759,449 checkpoint bytes. Base: `google/gemma-4/transformers/gemma-4-12b-it/2`; saved preparation: version 1 of `nitishsongara/afterfix-checkpoint-cpu`.

The public dataset layout places checkpoint files at its root rather than inside an extra `checkpoint` directory. When available, point the [reproduction adapter](nf4/adapter/README.md) at the directory containing `config.json` and `model.safetensors.index.json`. The [checkpoint manifest](nf4/companion-metadata/nf4-checkpoint-manifest.json) applies to those exact files.

The [adapter archive](archives/afterfix-nf4-adapter-v1.zip) and [checksum](archives/afterfix-nf4-adapter-v1.zip.sha256) are included. It changes access for new original/H08 replications only; frozen historical jobs and v3 QAT generation remain separate. Prompts, worker code, decoding and budgets are unchanged. A new replication must keep its own outputs.

Six historical metadata hashes and all shard sizes match. Full weight hashes were newly measured during retrieval and cannot retrospectively prove original inference bytes. Local file and copy verification passed; [the report](verification/nf4-access-v1.json) is preserved. GPU generation through the new mounted-input adapter remains untested.

Upstream Apache 2.0, Google attribution and [modification notices](nf4/companion-metadata/MODIFICATIONS.md) remain applicable. Historical pending manuscript-license text in preserved v1 records is superseded by the current root license scope.
