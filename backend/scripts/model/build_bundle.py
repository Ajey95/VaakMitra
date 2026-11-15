"""Package and verify an immutable VaakMitra word-model bundle v2."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.artifacts import (  # noqa: E402
    ArtifactFile,
    ArtifactFiles,
    BundleManifest,
    ReleaseMetadata,
    bundle_signing_input_sha256,
    verify_bundle,
)
from app.vaakmitra_word.model import sha256_file  # noqa: E402


FILENAMES = {
    "model": "model.nemo",
    "vocabulary": "vocabulary.json",
    "classifier": "word-classifier.npz",
    "reference_bank": "reference-bank.npz",
    "calibration": "calibration.json",
    "dataset_manifest": "dataset-manifest.jsonl",
    "canary_manifest": "canary-suite.json",
    "canary_run": "canary-run.json",
    "vad_config": "vad-config.json",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in FILENAMES:
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path,
                            required=name not in {"canary_run", "vad_config"})
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--rollback-bundle-hash", required=True)
    parser.add_argument("--deployment-mode", choices=("engineering", "production"), default="engineering")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    if args.deployment_mode == "production" and args.canary_run is None:
        parser.error("production bundles require --canary-run")
    if args.deployment_mode == "production" and args.vad_config is None:
        parser.error("production bundles require --vad-config")

    sources = {name: getattr(args, name) for name in FILENAMES if getattr(args, name) is not None}
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"{missing[0]}_unavailable")
    args.output_dir.mkdir(parents=True)
    specs: dict[str, ArtifactFile] = {}
    for name, source in sources.items():
        destination = args.output_dir / FILENAMES[name]
        shutil.copy2(source, destination)
        specs[name] = ArtifactFile(path=destination.name, sha256=sha256_file(destination))

    vocabulary = json.loads((args.output_dir / FILENAMES["vocabulary"]).read_text(encoding="utf-8"))
    release = ReleaseMetadata(
        code_commit=args.code_commit.lower(),
        rollback_bundle_hash=args.rollback_bundle_hash.lower(),
        signing_input_sha256="0" * 64,
    )
    manifest = BundleManifest(
        schema_version="vaakmitra-word-bundle-2",
        deployment_mode=args.deployment_mode,
        vocabulary_version=str(vocabulary["version"]),
        artifacts=ArtifactFiles(**specs),
        release=release,
    )
    release = release.model_copy(update={"signing_input_sha256": bundle_signing_input_sha256(manifest)})
    manifest = manifest.model_copy(update={"release": release})
    config_path = args.output_dir / "bundle.json"
    config_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    verification = verify_bundle(config_path)
    if not verification.engineering_ready or (args.deployment_mode == "production" and not verification.ready):
        raise RuntimeError(f"bundle_verification_failed:{','.join(verification.reasons)}")
    print(verification.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
