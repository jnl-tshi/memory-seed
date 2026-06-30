#!/usr/bin/env python3
"""
voxcpm_narrate.py — personal narration generator using VoxCPM2.

Standalone authoring tool. It is intentionally OUTSIDE the memory-seed package
(it lives under demo/tools/, which is untracked local housekeeping) so Memory
Seed never gains a CUDA/PyTorch dependency. It reads the demo's narration
scripts (assets/narration*.txt) and writes a matching .wav next to each one,
using VoxCPM2 with a pinned seed for reproducible takes.

Environment:
    Run this under the dedicated `voxcpm` conda env (kept separate from other
    envs because VoxCPM2 pins transformers 5.x, which conflicts with libraries
    like sentence-transformers). On this machine:
        C:\\Users\\johnn\\anaconda3\\envs\\voxcpm\\python.exe demo/tools/voxcpm_narrate.py ...
    To recreate the env elsewhere (one-time, CUDA-12 / PyTorch >= 2.5 GPU such as an RTX 4060):
        conda create -n voxcpm python=3.11 -y
        pip install torch --index-url https://download.pytorch.org/whl/cu126
        pip install voxcpm soundfile
        pip install scipy   # optional, only for --target-sr downsampling

Examples (prefix with the voxcpm env's python.exe as above):
    # Default voice, generate a .wav beside every assets/narration*.txt:
    python demo/tools/voxcpm_narrate.py

    # Clone a signature voice from a short reference clip (best for branding):
    python demo/tools/voxcpm_narrate.py --reference-wav my_voice.wav \
        --reference-text "exact transcript of my_voice.wav"

    # Preview what would be generated, change nothing:
    python demo/tools/voxcpm_narrate.py --dry-run

    # One specific line, downsampled to 24 kHz to match the project:
    python demo/tools/voxcpm_narrate.py --pattern narration-cta-1.txt --target-sr 24000

Notes:
    - VoxCPM2 outputs native 48 kHz. HyperFrames accepts that; --target-sr is only
      if you want to match an existing 24 kHz asset set.
    - Output is one-time and committed into assets/, so generation speed is irrelevant.
    - Diffusion sampling is stochastic; --seed pins it so an approved take re-renders.
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import sys
from pathlib import Path

# Default location of the demo narration scripts, relative to the repo root
# (this file lives at demo/tools/, so the repo root is two levels up).
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSETS = REPO_ROOT / "demo" / "assets"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate narration .wav files from .txt scripts using VoxCPM2.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--assets-dir", type=Path, default=DEFAULT_ASSETS,
                   help="Directory containing narration*.txt scripts.")
    p.add_argument("--pattern", default="narration*.txt",
                   help="Glob (within --assets-dir) selecting which scripts to render.")
    p.add_argument("--reference-wav", type=Path, default=None,
                   help="Reference clip to clone a signature voice from.")
    p.add_argument("--reference-text", default=None,
                   help="Transcript of --reference-wav (enables higher-fidelity cloning).")
    p.add_argument("--model-id", default="openbmb/VoxCPM2", help="VoxCPM model id.")
    p.add_argument("--seed", type=int, default=12345, help="Random seed for reproducible takes.")
    p.add_argument("--cfg", type=float, default=2.0, help="Guidance (cfg_value); higher = closer to text.")
    p.add_argument("--timesteps", type=int, default=10, help="Diffusion inference timesteps.")
    p.add_argument("--target-sr", type=int, default=None,
                   help="If set, downsample output to this sample rate (needs scipy).")
    p.add_argument("--overwrite", action="store_true",
                   help="Regenerate even if the .wav already exists.")
    p.add_argument("--dry-run", action="store_true",
                   help="List what would be generated and exit.")
    return p.parse_args(argv)


def seed_everything(seed: int) -> None:
    """Pin every RNG VoxCPM2 might touch so an approved take reproduces."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def maybe_resample(wav, src_sr: int, target_sr: int | None):
    """Optionally downsample; returns (wav, sample_rate). Fails loud if scipy missing."""
    if target_sr is None or target_sr == src_sr:
        return wav, src_sr
    try:
        from math import gcd
        from scipy.signal import resample_poly
    except ImportError:
        sys.exit("--target-sr needs scipy: pip install scipy (or omit --target-sr for native 48 kHz).")
    g = gcd(int(src_sr), int(target_sr))
    return resample_poly(wav, target_sr // g, src_sr // g), target_sr


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    assets_dir: Path = args.assets_dir
    if not assets_dir.is_dir():
        sys.exit(f"assets dir not found: {assets_dir}")

    scripts = sorted(Path(pth) for pth in glob.glob(str(assets_dir / args.pattern)))
    if not scripts:
        sys.exit(f"no scripts matched {args.pattern!r} in {assets_dir}")

    if args.reference_text and not args.reference_wav:
        sys.exit("--reference-text requires --reference-wav.")
    if args.reference_wav and not args.reference_wav.is_file():
        sys.exit(f"reference wav not found: {args.reference_wav}")

    targets = [(s, s.with_suffix(".wav")) for s in scripts]
    print(f"Found {len(targets)} script(s) in {assets_dir}:")
    for src, dst in targets:
        state = "exists (skip)" if dst.exists() and not args.overwrite and not args.dry_run else "generate"
        print(f"  {src.name:<28} -> {dst.name:<28} [{state}]")

    if args.dry_run:
        return 0

    # Heavy imports happen only for a real run, so --dry-run works with no GPU/torch.
    try:
        import soundfile as sf
        from voxcpm import VoxCPM
    except ImportError as exc:
        sys.exit(f"missing dependency ({exc.name}). Install: pip install voxcpm soundfile")

    seed_everything(args.seed)
    print(f"Loading {args.model_id} (seed={args.seed}) ...")
    model = VoxCPM.from_pretrained(args.model_id, load_denoiser=False)
    sample_rate = model.tts_model.sample_rate

    clone_kwargs = {}
    if args.reference_wav:
        clone_kwargs["reference_wav_path"] = str(args.reference_wav)
        if args.reference_text:
            # "Ultimate cloning": reference + its transcript for higher fidelity.
            clone_kwargs["prompt_wav_path"] = str(args.reference_wav)
            clone_kwargs["prompt_text"] = args.reference_text

    generated = 0
    for src, dst in targets:
        if dst.exists() and not args.overwrite:
            print(f"  skip {dst.name} (exists; use --overwrite to replace)")
            continue
        text = src.read_text(encoding="utf-8").strip()
        if not text:
            print(f"  skip {src.name} (empty)")
            continue
        print(f"  generating {dst.name} ...")
        # Re-pin the seed before each line so output is independent of order.
        seed_everything(args.seed)
        wav = model.generate(
            text=text,
            cfg_value=args.cfg,
            inference_timesteps=args.timesteps,
            **clone_kwargs,
        )
        wav, out_sr = maybe_resample(wav, sample_rate, args.target_sr)
        sf.write(str(dst), wav, out_sr)
        generated += 1
        print(f"    wrote {dst}  ({out_sr} Hz)")

    print(f"Done. Generated {generated} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
