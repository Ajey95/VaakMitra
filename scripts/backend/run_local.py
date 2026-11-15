"""Start the isolated WSL reference backend with real local MongoDB and artifacts.

DEC-013/018: development host only. Run with the existing NeMo Python environment.
No credentials are printed; runtime credentials live in an owner-only directory.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tarfile
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path("/home/vab/.local/share/vaakmitra/backend-lab")
ARCHIVE = RUNTIME / "downloads/mongodb-linux-x86_64-ubuntu2404-8.0.32.tgz"
DEFAULT_FILES = {
    "model": Path("/mnt/d/VaakMitraModels/ta-word-v1/upstream/indicconformer_stt_ta_hybrid_rnnt_large.nemo"),
    "vocabulary": Path("/mnt/d/VaakMitraData/manifests/ta-v1-engineering.json"),
    "classifier": Path("/mnt/d/VaakMitraData/artifacts/engineering/word-classifier.npz"),
    "reference_bank": Path("/mnt/d/VaakMitraData/artifacts/engineering/reference-bank.npz"),
    "calibration": Path("/mnt/d/VaakMitraData/artifacts/engineering/calibration.json"),
    "dataset_manifest": Path("/mnt/d/VaakMitraData/manifests/adult-calibration-evidence.jsonl"),
}


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else _digest(source)


def _digest(source):
    value = hashlib.sha256()
    for block in iter(lambda: source.read(1024 * 1024), b""):
        value.update(block)
    return value.hexdigest()


def select_engineering_evidence(files, evidence_dir):
    """DATA-013: select only a completed, unapproved adult engineering rebuild."""
    paths = {name: evidence_dir / name for name in
             ("calibration.json", "evidence.jsonl", "provenance.json", "report.json")}
    if not all(path.is_file() and path.stat().st_size for path in paths.values()):
        raise RuntimeError("engineering_rebuild_incomplete")
    try:
        calibration = json.loads(paths["calibration.json"].read_text(encoding="utf-8"))
        provenance = json.loads(paths["provenance.json"].read_text(encoding="utf-8"))
        report = json.loads(paths["report.json"].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("engineering_rebuild_incomplete") from exc
    if (calibration.get("approved") is not False or report.get("approved") is not False
            or report.get("human_approved") is not False or report.get("scoring_ready") is not False
            or provenance.get("approved") is not False or provenance.get("scoring_ready") is not False):
        raise RuntimeError("engineering_rebuild_not_unapproved")
    if (report.get("usable_attempt_count", 0) < 1
            or calibration.get("population") != "adult_only_engineering"
            or provenance.get("population") != "adult_only_engineering"
            or calibration.get("dataset_manifest_hash") != digest(paths["evidence.jsonl"])
            or report.get("calibration_hash") != digest(paths["calibration.json"])
            or not calibration.get("live_pipeline_hash")
            or calibration["live_pipeline_hash"] != provenance.get("live_pipeline_hash")
            or calibration["live_pipeline_hash"] != report.get("live_pipeline_hash")):
        raise RuntimeError("engineering_rebuild_incomplete")
    return {**files, "calibration": paths["calibration.json"],
            "dataset_manifest": paths["evidence.jsonl"]}


def configure():
    # DEC-022: pin the complete adult-only rebuild for the local website demo.
    evidence_dir = os.getenv("VAAKMITRA_ENGINEERING_EVIDENCE_DIR",
                             "/mnt/d/VaakMitraData/artifacts/live-rebuild-2026-09-12-r4")
    files = select_engineering_evidence(DEFAULT_FILES, Path(evidence_dir))
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    RUNTIME.chmod(0o700)
    secret_path = RUNTIME / "credentials.json"
    if secret_path.exists():
        credentials = json.loads(secret_path.read_text())
    else:
        credentials = {"mongo_password": secrets.token_urlsafe(32), "jwt_secret": secrets.token_urlsafe(48),
                       "admin_password": secrets.token_urlsafe(32)}
        fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(credentials, stream)
    expected = ARCHIVE.with_suffix(".tgz.sha256").read_text().split()[0]
    if digest(ARCHIVE) != expected:
        raise RuntimeError("MongoDB archive hash mismatch")
    mongo_dir = RUNTIME / "mongodb-linux-x86_64-ubuntu2404-8.0.32"
    binary = mongo_dir / "bin/mongod"
    if not binary.exists():
        with tarfile.open(ARCHIVE) as archive:
            for member in archive.getmembers():
                target = (RUNTIME / member.name).resolve()
                if not target.is_relative_to(RUNTIME) or member.issym() or member.islnk():
                    raise RuntimeError("Unsafe MongoDB archive member")
            archive.extractall(RUNTIME)
    data = RUNTIME / "mongo-data"
    data.mkdir(exist_ok=True, mode=0o700)
    from pymongo import MongoClient
    anonymous = MongoClient("mongodb://127.0.0.1:27018", serverSelectionTimeoutMS=2000)
    try:
        anonymous.admin.command("ping")
    except Exception:
        subprocess.run([str(binary), "--bind_ip", "127.0.0.1", "--port", "27018", "--auth",
                        "--dbpath", str(data), "--logpath", str(RUNTIME / "mongod.log"),
                        "--pidfilepath", str(RUNTIME / "mongod.pid"), "--fork"], check=True)
    uri = "mongodb://vm_backend:" + quote(credentials["mongo_password"], safe="") + "@127.0.0.1:27018/?authSource=admin"
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("listDatabases", nameOnly=True)
    except Exception:
        # MongoDB's first-user localhost exception; fails if a different DB owns this port.
        anonymous.admin.command("createUser", "vm_backend", pwd=credentials["mongo_password"],
                                roles=[{"role": "root", "db": "admin"}])
        client.close()
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.admin.command("listDatabases", nameOnly=True)
    anonymous.close()
    client.close()
    config = {"schema_version": "vaakmitra-local-diagnostics-1", "device": os.getenv("VAAKMITRA_DIAGNOSTIC_DEVICE", "cuda"),
              **{name: {"path": str(path), "sha256": digest(path)} for name, path in files.items()}}
    vad_model = RUNTIME / 'downloads/silero_vad.onnx'
    if digest(vad_model) != '1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3':
        raise RuntimeError('VAD model integrity mismatch')
    vad_config = RUNTIME / 'vad.json'
    vad_config.write_text(json.dumps({'schema_version': 'vaakmitra-vad-1', 'model_path': str(vad_model),
        'model_sha256': digest(vad_model), 'threshold': 0.5, 'min_speech_ms': 200, 'pause_tolerance_ms': 700}), encoding='utf-8')
    config['vad_config'] = {'path': str(vad_config), 'sha256': digest(vad_config)}
    config_path = RUNTIME / "engineering.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    os.environ.update(APP_ENV="development", MONGODB_URL=uri, DB_NAME="vaakmitra_backend_lab",
                      JWT_SECRET_KEY=credentials["jwt_secret"], ADMIN_EMAIL="operator@vaakmitra.example.org",
                      ADMIN_PASSWORD=credentials["admin_password"], VAAKMITRA_DIAGNOSTICS_ENABLED="true",
                      VAAKMITRA_DIAGNOSTIC_CONFIG=str(config_path), VAAKMITRA_BUNDLE_CONFIG="",
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1",
                      CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8002")
    return credentials


if __name__ == "__main__":
    configure()
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002, access_log=False)
