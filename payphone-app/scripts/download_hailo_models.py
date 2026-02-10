#!/usr/bin/env python3
"""Download Hailo Whisper model files for Hailo-10H NPU.

Downloads pre-compiled HEF files and CPU-side embedding arrays needed
by the Wyoming Hailo Whisper server (services/wyoming_whisper_server.py).

Files downloaded per variant:
    - {variant}-whisper-encoder-10s.hef      (encoder for Hailo NPU)
    - {variant}-whisper-decoder-fixed-sequence.hef  (decoder for Hailo NPU)
    - token_embedding_weight_{variant}.npy   (CPU-side vocab embeddings)
    - onnx_add_input_{variant}.npy           (CPU-side positional embeddings)

Source: Hailo Application Code Examples
    https://github.com/hailo-ai/Hailo-Application-Code-Examples

Usage:
    python scripts/download_hailo_models.py                    # tiny (default)
    python scripts/download_hailo_models.py --variant base     # base model
    python scripts/download_hailo_models.py --output-dir /path/to/models
"""

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Base URL for Hailo's public S3 bucket
S3_BASE = "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources"

# Download manifest: (variant, filename, relative S3 path)
# NPY files are confirmed available. HEF files follow the same S3 convention
# used by Hailo-Application-Code-Examples/download_resources.py.
MODELS = {
    "tiny": {
        "encoder_hef": {
            "filename": "tiny-whisper-encoder-10s.hef",
            "url": f"{S3_BASE}/hefs/h10h/tiny/tiny-whisper-encoder-10s.hef",
        },
        "decoder_hef": {
            "filename": "tiny-whisper-decoder-fixed-sequence.hef",
            "url": f"{S3_BASE}/hefs/h10h/tiny/tiny-whisper-decoder-fixed-sequence.hef",
        },
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
        "encoder_hef": {
            "filename": "tiny.en-whisper-encoder-10s.hef",
            "url": f"{S3_BASE}/hefs/h10h/tiny.en/tiny_en-whisper-encoder-10s.hef",
        },
        "decoder_hef": {
            "filename": "tiny.en-whisper-decoder-fixed-sequence.hef",
            "url": f"{S3_BASE}/hefs/h10h/tiny.en/tiny_en-whisper-decoder-fixed-sequence.hef",
        },
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
        "encoder_hef": {
            "filename": "base-whisper-encoder-10s.hef",
            "url": f"{S3_BASE}/hefs/h10h/base/base-whisper-encoder-10s.hef",
        },
        "decoder_hef": {
            "filename": "base-whisper-decoder-10s-out-seq-64.hef",
            "url": f"{S3_BASE}/hefs/h10h/base/base-whisper-decoder-10s-out-seq-64.hef",
        },
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

# Note: base model uses "decoder-10s-out-seq-64" (64-token output) instead of
# "decoder-fixed-sequence" (32-token). The Wyoming server discovers seq_len
# from the HEF at runtime, so this works automatically.


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
        if e.code == 404:
            print(
                "    This file may not be available from S3. See README for\n"
                "    alternative: compile HEF from ONNX using Hailo DFC Docker."
            )
        return False
    except urllib.error.URLError as e:
        print(f"\r    FAILED — {e.reason}")
        return False
    except Exception as e:
        print(f"\r    FAILED — {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Hailo Whisper model files for Hailo-10H"
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="tiny",
        choices=list(MODELS.keys()),
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

    if variant not in MODELS:
        print(f"Unknown variant: {variant}")
        print(f"Available: {', '.join(MODELS.keys())}")
        sys.exit(1)

    print(f"Downloading Hailo Whisper models (variant={variant})")
    print(f"Output directory: {output_dir}")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)

    files = MODELS[variant]
    success = 0
    failed = 0

    for key, info in files.items():
        dest = output_dir / info["filename"]
        desc = f"{key} ({info['filename']})"
        if download_file(info["url"], dest, desc):
            success += 1
        else:
            failed += 1

    print()
    print(f"Done: {success} downloaded, {failed} failed")

    if failed > 0:
        print()
        print("Some files failed to download. Options:")
        print("  1. Re-run this script to retry")
        print("  2. Download manually from Hailo Developer Zone:")
        print("     https://hailo.ai/developer-zone/software-downloads/")
        print("  3. Compile HEF files from ONNX using Hailo DFC Docker:")
        print("     See the plan in the project docs for DFC compilation steps")
        sys.exit(1)

    # Verify files
    print()
    print("Verifying downloaded files...")
    all_ok = True
    for key, info in files.items():
        path = output_dir / info["filename"]
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  OK  {info['filename']} ({size_mb:.1f} MB)")
        else:
            print(f"  MISSING  {info['filename']}")
            all_ok = False

    if all_ok:
        print()
        print("All model files ready. Start the Wyoming server:")
        print(f"  python services/wyoming_whisper_server.py --model-dir {output_dir}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
