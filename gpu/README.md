# AfterFix GPU inference supplement v3

Local release candidate, 24 October 2026. This supplement contains frozen inference source and instructions. It has passed offline checks, but it has not been uploaded or rerun on a GPU as part of release preparation. The sole author is Nitish Songara, Independent researcher. Original code and synthetic benchmark use Apache 2.0; see [license scope](LICENSE_SCOPE.md). Public release remains pending. No model weights or credentials are included.

Use the separate `afterfix-cpu-v5.zip` for quick reproduction of the paper's saved results. This supplement is for inspecting or launching new generation runs, which can consume cloud quota and need network/model access. New outputs must be labeled as replications and kept separate from the paper's archived observations.

## Contents and study boundaries

| Job key | Evidence represented | Scheduled attempts | Frozen code |
|---|---|---:|---|
| original-batch-1 | Original 12B NF4, first six cases | 18 | [Launcher](jobs/original-batch-1/pilot.py), [readable payload](jobs/original-batch-1/payload/) |
| original-batch-2 | Original 12B NF4, next six cases | 18 | [Launcher](jobs/original-batch-2/pilot.py), [readable payload](jobs/original-batch-2/payload/) |
| original-batch-3-retry | Original 12B NF4, successful permitted replacement | 18 | [Launcher](jobs/original-batch-3-retry/pilot.py), [readable payload](jobs/original-batch-3-retry/payload/) |
| original-batch-4 | Original 12B NF4, final six cases | 18 | [Launcher](jobs/original-batch-4/pilot.py), [readable payload](jobs/original-batch-4/payload/) |
| h08 | Separate corrected H08 run, all three methods | 3 | [Launcher](jobs/h08/pilot.py), [readable payload](jobs/h08/payload/) |
| v3 | Matched 31B then 12B QAT comparison | 144 | [Launcher](jobs/v3/pilot.py), [readable payload](jobs/v3/payload/) |
| checkpoint | Original CPU NF4 preparation, no benchmark | 0 | [Preparation source](jobs/checkpoint/prepare.py) |

Every launcher and historical metadata file is copied byte-for-byte. `payload/` contains the exact literal `FILES` dictionary extracted without executing the launcher. The inference payloads contain public tasks, prompts and tools, not reference answers, graders or private variants. The source map and returned-file comparisons in [build provenance](provenance/build.json) document the chain back to the saved jobs. [JOBS.json](JOBS.json) lists job keys and paths.

The original H08 query-authorizer defect remains in the original jobs. The corrected H08 run uses its own fixed source. V3 uses the corrected harness with its larger budget and verified BOS transport. Earlier failed startup jobs and the standalone BOS smoke are not additional benchmark attempts and are not silently substituted for any of these jobs.

## Offline verification

Use Python 3.12 or later with the standard library:

```sh
python -I -B verify.py
```

This checks every manifest hash, extracted payload, embedded payload manifest, schedule and Python syntax. It tests the packaged v3 BOS handling and GPU-placement validation with mocked inputs. It neither starts a server nor accesses the network, loads weights or uses a GPU. `MANIFEST.json` covers package contents; historical seals in `provenance/` cover the larger original workspace and are not expected to resolve entirely inside this supplement.

The release verifier also exercises staging and confirms that its generated launcher is unchanged. Passing these CPU checks does not prove that current Kaggle images, checkpoint permissions or download endpoints still permit a new run.

## Hardware, dependencies and limits

These launchers target Linux Kaggle sessions and write to `/kaggle/working`. Do not run them as ordinary local Windows or macOS scripts. Run each original batch or H08 in its own fresh session. V3 runs both models serially in one fresh session and verifies exactly two T4 GPUs. The NF4 workers load the model onto one GPU; selecting Kaggle T4 allocation may expose two devices, but their memory is not pooled by that worker.

| Setting | Original and H08 | Matched v3 |
|---|---|---|
| Model | Prepared 12B NF4 | Official 31B and 12B QAT Q4_0 GGUF |
| Runtime | Transformers 5.20.2, accelerate 1.15.0, bitsandbytes 0.50.2, kagglehub 1.0.2 | llama.cpp b11836, pinned Linux CUDA 12.8 archives |
| Recorded environment | Python 3.13.15, PyTorch 2.11.0+cu128, SQLite 3.45.1 | Python 3.13.15, SQLite 3.45.1; PyTorch is not the inference backend |
| Allocation | Model on one T4 | All layers split across two T4s |
| Turns / total output / per response / input tokens | 6 / 1,536 / 512 / 4,096 | 12 / 4,096 / 1,024 / 8,192 |
| Attempt / generation / loading cutoff | 240 s / 80 s / 300 s | 240 s / 80 s / 300 s |
| Model download cutoff | 180 s | 900 s per model |
| Notebook ceiling | 5,310 s per job | 42,300 s |
| Controller/worker ceiling | Worker 4,950 s, bounded by notebook remainder | Controller 41,400 s; each model worker at most 18,300 s |

Greedy decoding, seed 17 and disabled thinking are preserved. Malformed actions consume turns. No free formatting retries, model fallback, or selective benchmark retry is added. Timeouts remain outcomes under the frozen protocol. Loading or download failures must remain infrastructure failures, not be filled with invented model failures or scores from another run.

V3 requires at least 30 GiB of free scratch space for the pinned model/runtime stage. Its archived completion took 127.68 minutes, but that is not a prediction or a new timing measurement. Quota availability and current hardware allocation must be checked before launching. This preparation starts no cloud jobs.

The [recorded environment](provenance/environments.json) is descriptive. The original controller pins four Python dependencies, but Kaggle's base image and its transitive dependencies were not fully locked. We do not provide a fabricated exact container image or dependency lock. Matching the recorded versions reduces drift but does not guarantee bitwise-identical generations or timings.

## Original NF4 checkpoint dependency

Original/H08 source pins the input model to `google/gemma-4/transformers/gemma-4-12b-it/2`. It downloads the prepared artifact from version 1 of `nitishsongara/afterfix-checkpoint-cpu`, through Kaggle's notebook-output resolver. The destination must have access to that artifact. The release preparation did not change its visibility or recheck external permissions.

The [CPU preparation job](jobs/checkpoint/prepare.py) and its [recorded metadata](jobs/checkpoint/kernel-metadata.recorded.json) are included. It uses CPU bitsandbytes NF4 double quantization with FP16 compute, saves shards and tokenizer/processor files, then reloads and checks finite logits. This is not the official QAT checkpoint. It requires the pinned original model attached under `/kaggle/input`, enough CPU RAM/storage for preparation, and no GPU. The historical preparation metadata and environment are in [preparation evidence](provenance/checkpoint-preparation.json). No hardware-independent minimum RAM was established.

Before public release, choose one of two explicitly documented access arrangements: make the recorded preparation source/output available under applicable terms, or publish a separately versioned reproduction adapter pointing to a newly prepared checkpoint. A new preparation is not automatically byte-identical to the old one. Merely creating a checkpoint under a new username does not redirect the frozen downloader. Do not edit the recorded payload and continue calling it the original experiment.

The old NF4 checks record source identity, quantization settings, shard sizes and tokenizer hashes. They did not establish a full cryptographic hash for every weight shard. This supplement does not retroactively claim that stronger guarantee. V3, in contrast, pins full GGUF file sizes and SHA-256 hashes.

## V3 model pins and BOS handling

The complete [runtime plan](jobs/v3/payload/deep-results/plan.json) contains download URLs, runtime archive hashes, schedule and limits. Its models are:

| Model | Repository | Revision |
|---|---|---|
| 31B | `google/gemma-4-31B-it-qat-q4_0-gguf` | `59dde24573e7e61570dba08b18a2e1fe246955ed` |
| 12B | `google/gemma-4-12B-it-qat-q4_0-gguf` | `29d097773436b69ff9feafd636ab4cf873786537` |

31B weight SHA-256: `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b`.

12B weight SHA-256: `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b`.

The [transport](jobs/v3/payload/deep_http.py) normalizes to exactly one leading `<bos>`, tokenizes with `add_special=False` and `parse_special=True`, requires token ID 2 exactly once at the beginning, then sends the integer-token prompt. The [worker](jobs/v3/payload/deep_worker.py) checks native BOS metadata, disabled-thinking template shape, prompt limits, complete GPU offload and both GPU buffers. It validates generation with a small non-benchmark smoke before case attempts. These gates are part of the preserved run protocol.

## Prepare a new Kaggle job without running it

Keep the extracted supplement unchanged. The helper below creates a new staging directory outside it, copies the exact launcher, and writes metadata with your explicitly chosen NEW notebook ID. It refuses historical IDs and existing destinations. It does not authenticate, upload or run anything.

```sh
python -I -B stage_job.py --job v3 --id YOUR_USERNAME/afterfix-v3-replication --output ../staged-v3
```

Choose a key from `JOBS.json` for another job. Each original batch needs a different staging directory and notebook ID. `checkpoint` stages CPU preparation with GPU disabled and the recorded model source attached. It still needs a deliberate artifact-access plan before original/H08 generation can work under a different account.

Inspect the staged `kernel-metadata.json`, set up Kaggle authentication outside the package, confirm model access and free quota, and verify available accelerators. The following commands are instructions for a future deliberate run. They were not executed during preparation:

```sh
kaggle kernels push -p ../staged-v3 --accelerator NvidiaTeslaT4 --timeout 42300
kaggle kernels status YOUR_USERNAME/afterfix-v3-replication
kaggle kernels output YOUR_USERNAME/afterfix-v3-replication/1 -p ../new-v3-output
```

Replace the output version with the version actually returned by submission. Original/H08 launches use `--timeout 5310`; a CPU preparation launch omits the accelerator option and uses GPU-disabled metadata. The CLI push command uploads and starts execution by default. For a later metadata-only save, `--no-run` skips execution but still uploads. Commands and accelerator syntax were checked against the [official Kaggle CLI documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md) on 24 October 2026. No notebook IDs in historical metadata should be used as new submission targets.

## Retrieve and grade a new run separately

Download each run to its own new directory and retain all files. Verify payload hashes against the included source and inspect `summary.json` plus worker status. Original/H08 outputs are under `afterfix-results/`; v3 outputs are under `deep-results/`, with separate `31b/` and `12b/` stage folders. Keep partial results and infrastructure logs.

The CPU package has the correct per-study graders and expected historical outputs. Its standard `reproduce.py` intentionally asserts equality with historical observations, so do not substitute replication outputs into it. To score a new run, make a new versioned analysis using the appropriate packaged `source/afterfix/heldout_grade.py` and `heldout_evaluation.py`, seeds 0/7/19, and its own output directory. Never overwrite the archived raw/expected folders. A future replication analysis is separate work; this supplement provides frozen generation and does not invent new scores.

For audit of the existing paper, use CPU replay. Full native stream logs remain in the project archive, while the supplement includes generation code and selected recorded runtime evidence. This compact supplement is not an independent rerun of the entire experiment.

## Release status

The author is Nitish Songara, Independent researcher. Original code and benchmark use Apache 2.0. The manuscript uses CC BY 4.0 OR Apache 2.0. Public release is pending. Model/runtime licenses remain applicable; no model weights or third-party runtime binaries are redistributed here. A separate [release status](RELEASE_STATUS.md) records these boundaries. Nothing in these instructions authorizes publishing data or starting a cloud run automatically.

## Review version v3

Updates documentation and license metadata only. All historical launchers, payload files, model pins, verification and staging tools remain byte-identical to v2. Previous documentation is retained. See [NF4 companion and adapter](NF4_ACCESS.md) for the separately verified local access route. The frozen launchers still contain their historical resolver; use the separate adapter only for a new, explicitly labeled replication. Public access and adapter GPU execution remain untested.
