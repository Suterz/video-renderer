# Selected Drama 3 narrators

Listening decision: **Fish Audio Drama 3** is the selected model. **A, E and F** are the selected narrators; none of the three has been designated the sole default.

| Label | Reference |
|---|---|
| A | The original **Explanation B**, clipped at 20.15 s. No audio from the old Hook B. |
| E | Direct educator, clipped from E's own selected explanation at 20.17 s. |
| F | Warm documentary, clipped from F's own selected explanation at 21.23 s. |

The `*.safetensors` files are the encoded references from the actual audition, with their transcripts embedded. A seed alone does not select a narrator. Use the saved references for both hooks and explanations. `narrators.json` pins the model, codec, runtime revisions, reference hashes, source recording hashes and delivery settings. Model weights are installed outside Git.

## Reconstruct the worker

Use the ComfyUI and `PedroMarinhoDev/ComfyUI-Drama3` revisions in `narrators.json`. Install the latter under an isolated ComfyUI checkout's `custom_nodes/`. Fetch the model and codec from the pinned `PedroMarinhoDev/Drama-3-ComfyUI` repack revision and verify the SHA-256 values. Put `drama3_fp8experts_bf16.safetensors` in `models/diffusion_models/` and `drama3_codec.safetensors` in `models/vae/`. `worker-packages.txt` records the installed dependency versions on the verified worker. The workstation used Python 3.12.3, NVIDIA driver 580.178.04 and a single RTX 4090.

From that ComfyUI checkout, launch its isolated Python:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 /path/to/venv/bin/python -B main.py \
  --listen 127.0.0.1 --port 8960 --base-directory "$PWD" --disable-api-nodes
```

With the pinned local ComfyUI/Drama 3 worker listening on `127.0.0.1:8960`, run from the video-renderer checkout:

```sh
python3 daily_fish_audition.py /new/output/dir /path/to/worker/output \
  --narrator A --passage both
```

`--narrator E` and `--narrator F` select the other references. The command checks the reference hash, installs it into the worker's `drama3_voices` directory and saves the exact submitted graph and response beside the WAVs. Omit `--passage` to render both. This reproduces the voice reference and performance recipe, not a promise of bit-identical synthesis across machines. No production voice default is changed by the registry.

Built with Fish Audio. The model and codec are subject to the Fish Audio Community License v1.0 pinned in `narrators.json`; production commercial eligibility is not recorded by this selection.
