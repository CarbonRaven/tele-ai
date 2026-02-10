#!/usr/bin/env python3
"""Download Hailo Whisper model files for Hailo-10H NPU.

Downloads CPU-side embedding arrays from Hailo's public S3 bucket and
checks for HEF files needed by the Wyoming Whisper server.

Files needed per variant:
    - {variant}-whisper-encoder-10s.hef      (encoder for Hailo NPU)
    - {variant}-whisper-decoder-fixed-sequence.hef  (decoder for Hailo NPU)
    - token_embedding_weight_{variant}.npy   (CPU-side vocab embeddings)
    - onnx_add_input_{variant}.npy           (CPU-side positional embeddings)

NPY embedding files are publicly downloadable from Hailo's S3 bucket.
HEF files require one of:
    1. hailo-apps package: hailo-download-resources --group whisper_chat --arch hailo10h
    2. Hailo Developer Zone: https://hailo.ai/developer-zone/ (free account)
    3. Manual compilation with Hailo DFC v5.x Docker (see plan docs)

Usage:
    python scripts/download_hailo_models.py                    # tiny (default)
    python scripts/download_hailo_models.py --variant base     # base model
    python scripts/download_hailo_models.py --output-dir /path/to/models
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Base URL for Hailo's public S3 bucket
S3_BASE = "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources"

# NPY embedding files — publicly downloadable from Hailo S3
NPY_FILES = {
    "tiny": {
        "token_embeddings": {
            "filename": "token_embedding_weight_tiny.npy",
            "url": f"{S3_BASE}/npy%20files/whisper/decoder_assets/tiny/decoder_tokenization/token_embedding_weight_tiny.npy",
        },
        "pos_embeddings": {
            "filename": "onnx_add_input_tiny.npy",
            "url": f"{S3_BASE}/npy%20files/whisper/decoder_assets/tiny/decoder_tokenization/onnx_add_input_tiny.npy",
        },
    },
    "tiny.en": {
        "token_embeddings": {
            "filename": "token_embedding_weight_tiny.en.npy",
            "url": f"{S3_BASE}/npy%20files/whisper/decoder_assets/tiny.en/decoder_tokenization/token_embedding_weight_tiny.en.npy",
        },
        "pos_embeddings": {
            "filename": "onnx_add_input_tiny.en.npy",
            "url": f"{S3_BASE}/npy%20files/whisper/decoder_assets/tiny.en/decoder_tokenization/onnx_add_input_tiny.en.npy",
        },
    },
    "base": {
        "token_embeddings": {
            "filename": "token_embedding_weight_base.npy",
            "url": f"{S3_BASE}/npy%20files/whisper/decoder_assets/base/decoder_tokenization/token_embedding_weight_base.npy",
        },
        "pos_embeddings": {
            "filename": "onnx_add_input_base.npy",
            "url": f"{S3_BASE}/npy%20files/whisper/decoder_assets/base/decoder_tokenization/onnx_add_input_base.npy",
        },
    },
}

# HEF files — NOT publicly downloadable. Must be obtained separately.
# These are the expected filenames the Wyoming server looks for.
HEF_FILES = {
    "tiny": {
        "encoder_hef": "tiny-whisper-encoder-10s.hef",
        "decoder_hef": "tiny-whisper-decoder-fixed-sequence.hef",
    },
    "tiny.en": {
        "encoder_hef": "tiny.en-whisper-encoder-10s.hef",
        "decoder_hef": "tiny.en-whisper-decoder-fixed-sequence.hef",
    },
    "base": {
        "encoder_hef": "base-whisper-encoder-10s.hef",
        # Base model uses 64-token output sequence
        "decoder_hef": "base-whisper-decoder-10s-out-seq-64.hef",
    },
}


def download_file(url: str, dest: Path, desc: str) -> bool:
    """Download a file with progress reporting.

    Returns True on success, False on failure.
    """
    if dest.exists():
        print(f"  [skip] {desc} — already exists ({dest.name})")
        return True

    print(f"  [download] {desc}...")
    print(f"    URL: {url}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "payphone-ai/1.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunks = []

            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    print(
                        f"\r    {mb:.1f}/{total_mb:.1f} MB ({pct}%)",
                        end="",
                        flush=True,
                    )

            data = b"".join(chunks)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

            size_mb = len(data) / (1024 * 1024)
            md5 = hashlib.md5(data).hexdigest()[:8]
            print(f"\r    OK — {size_mb:.1f} MB (md5:{md5})")
            return True

    except urllib.error.HTTPError as e:
        print(f"\r    FAILED — HTTP {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\r    FAILED — {e.reason}")
        return False
    except Exception as e:
        print(f"\r    FAILED — {e}")
        return False


def try_hailo_download_resources(variant: str, output_dir: Path) -> bool:
    """Try downloading HEFs via hailo-download-resources CLI.

    Returns True if the command exists and succeeds.
    """
    if not shutil.which("hailo-download-resources"):
        return False

    print("  [hailo-download-resources] Found! Attempting HEF download...")
    try:
        result = subprocess.run(
            [
                "hailo-download-resources",
                "--group", "whisper_chat",
                "--arch", "hailo10h",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            print("    OK — HEFs downloaded via hailo-download-resources")
            return True
        else:
            print(f"    Failed: {result.stderr.strip()[:200]}")
            return False
    except Exception as e:
        print(f"    Failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Hailo Whisper model files for Hailo-10H"
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="tiny",
        choices=list(NPY_FILES.keys()),
        help="Whisper model variant (default: tiny)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "models",
        help="Output directory for model files",
    )
    args = parser.parse_args()

    variant = args.variant
    output_dir = args.output_dir

    print(f"Downloading Hailo Whisper models (variant={variant})")
    print(f"Output directory: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Download NPY embedding files (public S3) ---
    print()
    print("Step 1: Downloading NPY embedding files...")
    npy_ok = 0
    npy_fail = 0
    for key, info in NPY_FILES[variant].items():
        dest = output_dir / info["filename"]
        desc = f"{key} ({info['filename']})"
        if download_file(info["url"], dest, desc):
            npy_ok += 1
        else:
            npy_fail += 1

    # --- Step 2: Check / obtain HEF files ---
    print()
    print("Step 2: Checking HEF model files...")
    hef_filenames = HEF_FILES[variant]
    hefs_present = True
    for key, filename in hef_filenames.items():
        path = output_dir / filename
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  [skip] {key} — already exists ({filename}, {size_mb:.1f} MB)")
        else:
            hefs_present = False
            print(f"  [missing] {key} ({filename})")

    if not hefs_present:
        # Try hailo-download-resources first
        print()
        if try_hailo_download_resources(variant, output_dir):
            # Re-check
            hefs_present = all(
                (output_dir / fn).exists() for fn in hef_filenames.values()
            )

    # --- Summary ---
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    all_files = {}
    for key, info in NPY_FILES[variant].items():
        all_files[info["filename"]] = key
    for key, filename in hef_filenames.items():
        all_files[filename] = key

    all_ok = True
    for filename, key in all_files.items():
        path = output_dir / filename
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  OK      {filename} ({size_mb:.1f} MB)")
        else:
            print(f"  MISSING {filename}")
            all_ok = False

    if all_ok:
        print()
        print("All model files ready. Start the Wyoming server:")
        print(f"  python services/wyoming_whisper_server.py --model-dir {output_dir}")
    else:
        print()
        if not hefs_present:
            print("HEF files are missing. To obtain them:")
            print()
            print("  Option A — On Pi with hailo-apps installed:")
            print("    pip install hailo-apps-infra")
            print("    hailo-download-resources --group whisper_chat --arch hailo10h")
            print(f"    cp /path/to/downloaded/*.hef {output_dir}/")
            print()
            print("  Option B — Hailo Developer Zone (free account):")
            print("    https://hailo.ai/developer-zone/software-downloads/")
            print("    Download Whisper HEFs for Hailo-10H, then copy to models/")
            print()
            print("  Option C — Compile from ONNX with Hailo DFC v5.x Docker:")
            print("    git clone https://github.com/hailocs/hailo-whisper.git")
            print("    See project plan docs for full compilation steps")
            print()
            print(f"  Expected filenames in {output_dir}/:")
            for filename in hef_filenames.values():
                print(f"    {filename}")
        if npy_fail > 0:
            print()
            print("Some NPY downloads failed. Re-run this script to retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
