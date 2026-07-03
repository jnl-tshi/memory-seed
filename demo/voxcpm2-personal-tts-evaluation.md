---
memory-system-version: 2.7
tags:
  - memory-seed
  - demo
  - evaluation
  - tts
---

# VoxCPM2 as a personal pitch-narration tool — evaluation

**Date:** 2026-06-14
**Framing:** VoxCPM2 is being evaluated as a **personal tool on your own PC** for producing narration/voice on the videos you create to **pitch projects after development** — this HyperFrames demo and future ones. It is **not** proposed for inclusion in the Memory Seed seed/package; it would live in your authoring workflow and produce `.wav` assets you drop into a project.
**Your hardware:** RTX 4060, **8 GB VRAM** (Ada Lovelace, CUDA 12-capable).

---

## TL;DR — recommendation

**Yes — VoxCPM2 is a strong fit for your personal pitch-video workflow, and a clear quality ceiling above Kokoro.** On your RTX 4060 it runs locally at FP16 (~5 GB) with room to spare, and quantization (INT8 ~2.5 GB / INT4 ~1.2 GB) is there if you ever hit OOM on long inputs.

For **pitch-grade output** — the thing you actually care about here — VoxCPM2 gives you:
- **48 kHz, expressive, natural delivery** vs Kokoro's competent-but-flat 24 kHz preset voices;
- **A clone-once, reuse-everywhere signature narrator** — record ~10–30 s of a voice you like (your own, or a licensed/permitted sample) and get a consistent branded voice across every pitch video;
- **Text "voice design"** (describe a voice — age/tone/emotion — no reference needed) for quick per-project variation.

Keep **Kokoro as the zero-setup default committed in the demo** (so the repo stays runnable on any machine), but for the **hero pitch cut**, generate narration with VoxCPM2 and drop the `.wav`s in. Use the right tool per purpose: Kokoro for "it just works anywhere," VoxCPM2 for "this is the version I'm showing people."

---

## Does your RTX 4060 (8 GB) run it well?

Yes. The published "~8 GB VRAM" figure is conservative; the practical footprint is lower:

| Precision | VoxCPM2 (~2.3B) VRAM | On your 4060 8 GB |
|---|---|---|
| FP16 | ~5.0 GB | **Fits** with ~3 GB headroom for activations — fine for short narration |
| INT8 | ~2.5 GB | Comfortable; OOM safety net |
| INT4 | ~1.2 GB | Very comfortable; for long inputs or heavy multitasking |

- **Compute/speed:** RTF is ~0.30 on an RTX 4090. The 4060 is several times slower, so expect roughly **real-time to a few× real-time** (a 30 s clip in perhaps ~30–60 s — *estimate*, not measured). For narration you generate **once and commit**, this is irrelevant.
- **Practical tips:** close other VRAM consumers (browsers, other models) when running at FP16; if you OOM on a long line, split it (as the demo already does) or drop to INT8. CUDA 12 is supported on Ada, so no driver-class blockers.

Net: the 4060 removes the single biggest objection from a package-portability standpoint — *for you, it runs locally and offline.*

---

## What you're comparing against (current demo)

From `demo/.memory-seed/sessions/2026-05-27.md` and `demo/CLAUDE.md`:

- **Kokoro** TTS (`kokoro-onnx` + `soundfile`, voice `af_heart`) — ~82M params, **~27 MB**, **CPU**, 24 kHz, Apache-2.0; built into HyperFrames' `/hyperframes-media` skill.
- Narration is an **author-time step**: `.txt` → `.wav`, committed into `demo/assets/`, timed in `index.html`. (TTS is not a render-time dependency, so swapping engines doesn't touch HyperFrames' deterministic-render rule.)
- Recorded friction: unreliable SSML `<break>` timing → CTA split into two clips. (A control-API quirk, not a quality one — and the split-clip workaround is engine-independent.)

---

## What VoxCPM2 gives a pitch video

[OpenBMB VoxCPM2](https://huggingface.co/openbmb/VoxCPM2) — tokenizer-free, diffusion-autoregressive TTS, **~2.3B params, 48 kHz** (AudioVAE V2), Apache-2.0:

- **Naturalness & expressiveness** that reads as "produced," not "robotic preset" — the difference a viewer notices in the first five seconds of a pitch.
- **Zero-shot voice cloning** from a short clip → a **consistent signature voice** you reuse across every project's pitch. This is the standout benefit for your use case: brand recognition across a portfolio of demos.
- **Voice design from text** (gender/age/tone/emotion, no reference) → fast per-project voice variation without managing samples.
- **30 languages + 9 Chinese dialects** with auto language detection — useful if you ever localize a pitch.
- **State-of-the-art speaker similarity** ([85.4 % EN SIM vs ElevenLabs 61.3 %](https://medium.com/@tentenco/voxcpm2-the-open-source-voice-model-that-beats-elevenlabs-on-similarity-but-the-full-benchmark-ffe408b50b87)) — cloning actually sounds like the target.

### Quality, framed for pitch output

| Axis (weighted for pitch material) | Kokoro | VoxCPM2 |
|---|---|---|
| Naturalness / "produced" feel | Good | **Excellent** |
| Sample rate / fidelity | 24 kHz | **48 kHz** |
| Signature/branded voice (clone) | No | **Yes** |
| Per-project voice variety | Few presets | **Design + clone** |
| Emotion / pacing control | Limited | **Style controls** |
| Localization | English-centric | **30 languages** |
| Setup on your PC | trivial (CPU) | one-time (PyTorch+CUDA) |
| Cost / license | free, Apache-2.0 | **free, Apache-2.0** |

For the question "**how good an output can I create?**" — VoxCPM2 raises your ceiling meaningfully, and the 4060 makes that ceiling reachable locally and for free.

---

## Honest caveats

- **English is its strong lane.** Benchmarks are self-reported (no independent reproduction yet) and multilingual robustness is uneven (Arabic ~13 % WER, Czech ~24 % — intelligibility drops). For English pitch narration this isn't a concern; for localized pitches, **audition each language** before trusting it.
- **8 GB is the practical floor at FP16.** Short lines are fine; very long single utterances or running it alongside other GPU apps may OOM → split the line or use INT8/INT4.
- **Stochastic output.** Diffusion-AR sampling varies by seed — **pin a seed** so a re-render reproduces the take you approved.
- **One-time setup cost.** PyTorch ≥2.5 + CUDA ≥12 toolchain and the model weights — heavier than `pip install kokoro-onnx`, but a one-off on your machine.
- **It does not auto-fix the SSML-break issue.** Keep the split-clip approach for frame-accurate gaps regardless of engine.

---

## Recommended workflow (per-purpose, not all-or-nothing)

1. **Keep Kokoro committed as the demo default** — anyone (including CI / a fresh clone) can render the demo with no GPU. This preserves the project's portability.
2. **Install VoxCPM2 once on your PC** (your 4060): `pip install voxcpm` into a CUDA-12 / PyTorch ≥2.5 env (or use the vLLM-Omni path for speed).
3. **Clone or design your signature pitch voice** from a short reference; save the speaker prompt so every project reuses the same voice.
4. **Generate the hero-cut narration out-of-band**, pinned seed, 48 kHz; export and (optionally) downsample to match the project, then drop the `.wav`s into `assets/`. The composition timing is unchanged.
5. **A/B the first time:** render the demo once with Kokoro and once with the VoxCPM2 track and decide whether the lift is worth it for that audience. (If you want a lighter first trial, **VoxCPM-0.5B** is a smaller variant to gauge the quality delta.)

This gives you a **portable default** and a **premium pitch track** without coupling Memory Seed to a GPU dependency.

---

## Bottom line

- **Better output than Kokoro for pitching?** Yes — clearly, on naturalness, fidelity, expressiveness, and especially a reusable cloned/branded voice.
- **Good fit for your personal use on a 4060?** Yes — it runs locally at FP16 with headroom, it's free (Apache-2.0), and the one-time setup pays off across every future pitch video.
- **Fold it into Memory Seed?** No — and you weren't asking to. It stays a personal authoring tool that emits `.wav` assets; Kokoro remains the committed, GPU-free default for the demo.

---

## Sources

- [openbmb/VoxCPM2 — Hugging Face](https://huggingface.co/openbmb/VoxCPM2)
- [OpenBMB/VoxCPM — GitHub](https://github.com/OpenBMB/VoxCPM)
- [VoxCPM paper (arXiv 2509.24650)](https://arxiv.org/html/2509.24650v1)
- [VoxCPM2 VRAM requirements by precision — Spheron GPU recommender](https://www.spheron.network/tools/gpu-recommender/openbmb/VoxCPM2/)
- [VoxCPM2 vs ElevenLabs benchmark nuance — Medium](https://medium.com/@tentenco/voxcpm2-the-open-source-voice-model-that-beats-elevenlabs-on-similarity-but-the-full-benchmark-ffe408b50b87)
- [VoxCPM2 overview — aimodels.fyi](https://www.aimodels.fyi/models/huggingFace/voxcpm2-openbmb)
- [RTX 4060 8 GB for AI — budget GPU guide](https://willitrunai.com/blog/rtx-4060-budget-ai-guide)
- Demo context: `demo/.memory-seed/sessions/2026-05-27.md`, `demo/CLAUDE.md`
