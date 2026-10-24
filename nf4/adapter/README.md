# AfterFix NF4 reproduction adapter v1

Local review package. No upload, publication or GPU execution has occurred. This package contains no weights. It works with the separately prepared `afterfix-gemma4-12b-nf4-v1` checkpoint folder.

The original four successful NF4 batches and corrected H08 are supported. V3 uses separate QAT GGUF weights and is intentionally excluded. Original, H08 and v3 results remain separate and unchanged.

## Verify the saved weights

```sh
python -I -B nf4_checkpoint.py --checkpoint /absolute/path/to/afterfix-gemma4-12b-nf4-v1/checkpoint --report new-report.json
```

This reads and hashes all 21 files, checks quantization settings and shard inventory, and verifies the embedded manifest's hash. It does not load a model, contact Kaggle or use a GPU. The full weight hashes are release-time measurements, not hashes recorded during the original study. The checkpoint README documents provenance limitations.

## Stage a new replication

```sh
python -I -B stage_job.py --job original-batch-1 --id nitishsongara/afterfix-nf4-replication-batch-1 --checkpoint-path /kaggle/input/YOUR-ARTIFACT/checkpoint --output new-stage
```

Replace the path with the actual mounted directory after the artifact is eventually available. No such public artifact or path is claimed to exist now. Optionally provide `--dataset-source owner/slug` when the real input exists; this only writes local metadata. For testing a downloaded local checkpoint, the verifier above uses its actual local path. Staged GPU controllers remain Kaggle/Linux programs and must not be executed as ordinary local scripts.

The staging command verifies this package and each original embedded payload. It refuses historical notebook IDs and existing output directories. It creates a private-notebook metadata file, a new launcher, replication provenance and staged checksums. It neither calls Kaggle nor runs that launcher. Use one new ID and fresh session for each of the five jobs. `JOBS.json` lists the accepted keys.

## Exact changes

The only replaced experimental Python module is `afterfix/checkpoint_download.py`. It replaces the private notebook HTTP resolver with a fully hashed copy from the specified local/mounted checkpoint to temporary local storage. Three helper/config files are added. A replication record and updated payload manifest identify the new access path. Original launcher and metadata bytes are included under `historical/`.

Prompts, cases, model configuration, parser, worker/controller code, method order, schedule, decoding settings and budgets are unchanged. The inherited study seal is retained only as a historical reference; the modified payload has separate hashes. The generated launcher also refuses a non-Kaggle or already-used workspace. The new result folder contains `replication.json` so it is not mistaken for original observations.

The unchanged controller's **180-second artifact-access timeout** includes full copy and hashing. Slow mounts can fail this limit; no timeout is silently expanded and no unverified checkpoint fallback is allowed. After access, the historical loading/generation limits still apply. Dependencies are installed by the unchanged controller, so a future full run still needs network access for that step. This adapter only removes dependence on private notebook outputs.

`AFTERFIX_NF4_CHECKPOINT` can override the staged path; every byte must still match the pinned checkpoint manifest. A missing or modified file stops before worker launch. The local copy requires roughly another 7.71 GB of scratch space in addition to the source artifact. New replications must use separate output/analysis directories and never replace the CPU package's archived raw or expected results.

## Validation scope

The accompanying local verification report checks every file hash, safetensors structure, staging for all five jobs, immutable payload comparisons and negative integrity/staging controls. These checks do not establish GPU loading speed, current Kaggle download behavior, cross-account/public access or identical generated answers. A short future GPU smoke can check the new access path; no new full benchmark run is needed for the present paper claims.

## License

Original adapter code: [Apache 2.0](LICENSE), Copyright 2026 Nitish Songara. The separate checkpoint retains Google's base-model attribution and license notices. Author and project code-license decisions are confirmed. Manuscript licensing remains undecided. Nothing in these instructions authorizes publication or cloud execution.
