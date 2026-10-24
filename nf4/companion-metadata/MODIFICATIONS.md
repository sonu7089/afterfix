# Modification notices

This is a modified distribution of Google DeepMind's Gemma 4 12B instruction-tuned checkpoint. The historical preparation converted eligible linear weights to bitsandbytes NF4 with double quantization and FP16 compute. The base model was not fine-tuned on AfterFix.

All 13 `checkpoint/model-*-of-00013.safetensors` files are quantized/reserialized derivatives, replacing the upstream single `model.safetensors` file. `model.safetensors.index.json` records the new sharding. `config.json`, `generation_config.json`, `tokenizer_config.json` and associated processor/tokenizer files were saved through the historical Transformers preparation process. `AFTERFIX_PROVENANCE.json` is AfterFix-generated metadata. The exact recipe and preparation report are included.

The checkpoint files are preserved byte-for-byte as retrieved for this release; this packaging step performs no new quantization or metadata edits inside those files. The modification notice applies to the listed prepared files, with per-file hashes in the checkpoint manifest. The original upstream README is preserved separately. Its general model examples do not describe this NF4 representation.

The pinned upstream file inventory contains a README declaring Apache 2.0, but no separate LICENSE or NOTICE file. This artifact includes the standard Apache 2.0 license text and retains that upstream README. The third-party base model remains attributed to Google DeepMind.
