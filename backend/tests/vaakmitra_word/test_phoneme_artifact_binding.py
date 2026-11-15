import hashlib
import json

import numpy as np
import pytest
import soundfile as sf
from scripts.model.finetune_mobile_phoneme import (
    load_run,
    read_bound_waveform,
    sha,
    write,
)


def test_phn005_robustness_reads_hash_bound_pcm_source(tmp_path):
    path = tmp_path / "source.wav"
    sf.write(path, np.ones(4000, dtype=np.float32) * 0.1, 16000, subtype="PCM_16")
    row = {"audio_path": "source.wav", "audio_sha256": sha(path)}
    assert read_bound_waveform(row, tmp_path).shape == (4000,)
    sf.write(path, np.zeros(4000, dtype=np.float32), 16000, subtype="PCM_16")
    with pytest.raises(ValueError, match="source"):
        read_bound_waveform(row, tmp_path)
    row["audio_sha256"] = sha(path)
    sf.write(path, np.zeros(4000, dtype=np.float32), 8000, subtype="PCM_16")
    row["audio_sha256"] = sha(path)
    with pytest.raises(ValueError, match="PCM"):
        read_bound_waveform(row, tmp_path)


def fixture_run(root):
    source = root / "source"
    source.write_text("source")
    base = root / "base"
    base.write_text("weights")
    vocab = {"tokens": ["<blank>", "a"]}
    binding = {
        "source_sha256": sha(source),
        "base_sha256": sha(base),
        "vocabulary_sha256": hashlib.sha256(
            json.dumps(vocab, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
    }
    binding["binding_sha256"] = "run"
    write(
        root / "dataset.json",
        {
            "binding": binding,
            "rows": [{"speaker": "s", "audio_sha256": "x", "split": "train"}],
        },
    )
    write(root / "input-binding.json", {"dataset_sha256": sha(root / "dataset.json")})
    write(root / "vocabulary.json", vocab)
    np.save(root / "audio.npy", np.zeros((1, 48000), dtype=np.float32))
    write(
        root / "cache-complete.json",
        {
            "binding_sha256": "run",
            "shape": [1, 48000],
            "audio_sha256": sha(root / "audio.npy"),
        },
    )
    return source, base


def test_rejects_vocabulary_changed_after_checkpoint(tmp_path):
    source, base = fixture_run(tmp_path)
    load_run(tmp_path, source, base)
    write(tmp_path / "vocabulary.json", {"tokens": ["<blank>", "b"]})
    with pytest.raises(ValueError, match="vocabulary"):
        load_run(tmp_path, source, base)


def test_rejects_cache_tampering_and_incomplete_cache(tmp_path):
    source, base = fixture_run(tmp_path)
    array = np.load(tmp_path / "audio.npy", mmap_mode="r+")
    array[0, 0] = 1
    array.flush()
    del array
    with pytest.raises(ValueError, match="cache"):
        load_run(tmp_path, source, base)


def test_rejects_prepared_rows_changed_after_binding(tmp_path):
    source, base = fixture_run(tmp_path)
    meta = json.loads((tmp_path / "dataset.json").read_text())
    meta["rows"][0]["split"] = "evaluation"
    write(tmp_path / "dataset.json", meta)
    with pytest.raises(ValueError, match="rows"):
        load_run(tmp_path, source, base)


def test_phn001_expanded_tamil_metadata_is_read_as_utf8(tmp_path):
    source, base = fixture_run(tmp_path)
    path = tmp_path / "dataset.json"
    meta = json.loads(path.read_text())
    meta["rows"][0]["transcript"] = "வணக்கம்"
    write(path, meta)
    write(tmp_path / "input-binding.json", {"dataset_sha256": sha(path)})
    loaded, _ = load_run(tmp_path, source, base)
    assert loaded["rows"][0]["transcript"] == "வணக்கம்"


def test_phn001_extra_source_manifest_is_bound_before_loading(tmp_path):
    source, base = fixture_run(tmp_path)
    expansion = tmp_path / "expansion-manifest.json"
    write(expansion, {"training": [], "audit": []})
    meta = json.loads((tmp_path / "dataset.json").read_text())
    meta["binding"]["expansion_sha256"] = sha(expansion)
    write(tmp_path / "dataset.json", meta)
    write(
        tmp_path / "input-binding.json",
        {"dataset_sha256": sha(tmp_path / "dataset.json")},
    )
    load_run(tmp_path, source, base)
    write(expansion, {"training": ["changed"], "audit": []})
    with pytest.raises(ValueError, match="expansion"):
        load_run(tmp_path, source, base)
