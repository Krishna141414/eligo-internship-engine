"""One-command setup of the sentence model (docs/DECISIONS.md D-020).

    .\\.venv\\Scripts\\python.exe scripts\\setup_sentence_model.py

Downloads sentence-transformers/all-MiniLM-L6-v2 at the pinned Hugging Face revision (the only
step that needs internet), saves it to artifacts/models/sentence_model/ without a model card, and
verifies every file against the SHA-256 hashes in artifacts/manifest.json. After this, Eligo runs
fully offline. The model folder is git-ignored; this script (or the notebook) recreates it.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_core.artifacts import SENTENCE_MODEL_SUBDIR, verify_manifest, verify_sentence_model  # noqa: E402
from ml_core.config import ARTIFACTS_DIR, SENTENCE_MODEL_NAME, SENTENCE_MODEL_REVISION  # noqa: E402

Downloader = Callable[[Path, str, str], None]


def download_and_save(target: Path, name: str, revision: str) -> None:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(name, revision=revision, device="cpu")
    model.save(str(target), create_model_card=False)


def main(argv: list[str] | None = None, *, download: Downloader = download_and_save) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifacts-dir", type=Path, default=ARTIFACTS_DIR)
    args = parser.parse_args(argv)
    artifacts_dir: Path = args.artifacts_dir

    base = verify_manifest(artifacts_dir)
    if not base.ok and "manifest.json" in base.message:
        print(f"Can't set up the sentence model: {base.message}")
        return 1

    target = artifacts_dir / SENTENCE_MODEL_SUBDIR
    if target.exists():
        shutil.rmtree(target)
    print(f"Downloading {SENTENCE_MODEL_NAME} @ {SENTENCE_MODEL_REVISION[:12]} ...")
    download(target, SENTENCE_MODEL_NAME, SENTENCE_MODEL_REVISION)

    status = verify_sentence_model(artifacts_dir)
    if status.ok:
        print(f"Sentence model verified against manifest.json: {target}")
        print("Eligo can now run offline.")
        return 0
    print(f"Verification FAILED: {status.message}")
    for rel in status.missing:
        print(f"  missing:    {rel}")
    for rel in status.mismatched:
        print(f"  mismatched: {rel}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
