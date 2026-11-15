"""PHN-003/006 DEC-035: malformed manifests cannot mutate staged app assets."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/model/deploy_mobile_phoneme.ps1"
BEAM = {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 8}


def stage(tmp_path, change):
    shell = shutil.which("pwsh")
    if not shell:
        pytest.skip("PowerShell staging is tested where PowerShell is installed")
    script = tmp_path / "repo/backend/scripts/model/deploy_mobile_phoneme.ps1"
    script.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    artifact = tmp_path / "artifact"
    bundle = artifact / "bundle"
    bundle.mkdir(parents=True)
    for file, data in [
        ("phoneme.fp32.onnx", b"model"),
        ("vocabulary.json", b"vocabulary"),
        ("MODEL_CARD.txt", b"card"),
    ]:
        (bundle / file).write_bytes(data)
    (artifact / "instrumentation-assets").mkdir()
    (artifact / "instrumentation-assets/ATTRIBUTION.txt").write_text("test fixture")
    manifest = {
        "bundle_version": "phoneme-ta19-v2",
        "decoder": dict(BEAM),
        "input_samples": 48000,
        "approved_for_child_scoring": False,
        "production_ready": False,
        "model_file": "phoneme.fp32.onnx",
        "model_sha256": hashlib.sha256(b"model").hexdigest(),
        "vocabulary_sha256": hashlib.sha256(b"vocabulary").hexdigest(),
        "tokens": 61,
    }
    change(manifest)
    (bundle / "bundle.json").write_text(json.dumps(manifest), encoding="utf8")
    result = subprocess.run(
        [shell, "-NoProfile", "-File", str(script), "-ArtifactRoot", str(artifact)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result, tmp_path / "repo/SpeakEasyAndroid/app/src/main/assets"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda m: m.update(bundle_version="PHONEME-TA19-V2"),
        lambda m: m["decoder"].update(type="CTC_PREFIX_BEAM"),
        lambda m: m.update(
            decoder={key.upper(): value for key, value in m["decoder"].items()}
        ),
        lambda m: m.update(DECODER=m.pop("decoder")),
        lambda m: m.update(BUNDLE_VERSION=m.pop("bundle_version")),
        lambda m: m.update(model_file="PHONEME.FP32.ONNX"),
        lambda m: m.update(model_sha256=m["model_sha256"].upper()),
        lambda m: m["decoder"].update(beam_width=5.0),
        lambda m: m.update(input_samples="48000"),
        lambda m: m.update(tokens="61"),
        lambda m: m.update(approved_for_child_scoring="False"),
        lambda m: m.update(production_ready="False"),
    ],
)
def test_phn006_rejects_malformed_staging_before_copy(tmp_path, mutation):
    result, target = stage(tmp_path, mutation)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not target.exists(), "invalid artifact was copied before rejection"


@pytest.mark.parametrize("legacy", [False, True])
def test_phn006_stages_exact_current_and_legacy_contracts(tmp_path, legacy):
    def mutate(m):
        if legacy:
            m["bundle_version"] = "phoneme-ta19-v1"
            m.pop("decoder")

    result, target = stage(tmp_path, mutate)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (target / "vaakmitra/phoneme-ta19-v1/bundle.json").exists()
