"""DEC068/PHN008: retained research history cannot consume the disk reserves."""
from types import SimpleNamespace
import pytest
from app.vaakmitra_word.backbone_storage import storage_guard


def test_low_system_space_stops_before_creating_any_output(tmp_path,monkeypatch):
    monkeypatch.setattr('app.vaakmitra_word.backbone_storage.shutil.disk_usage',
        lambda path:SimpleNamespace(free=128*1024**2 if path.startswith('C')else 20*1024**3))
    with pytest.raises(OSError,match='reserve'):storage_guard(tmp_path)
    assert list(tmp_path.iterdir())==[]


def test_output_budget_includes_preserved_checkpoints_but_excludes_downloads(tmp_path,monkeypatch):
    monkeypatch.setattr('app.vaakmitra_word.backbone_storage.shutil.disk_usage',lambda _:SimpleNamespace(free=20*1024**3))
    (tmp_path/'models').mkdir();(tmp_path/'models/weights').write_bytes(b'x'*100)
    storage_guard(tmp_path,max_output_gib=10/1024**3)
    (tmp_path/'epoch.pt').write_bytes(b'x'*11)
    with pytest.raises(OSError,match='budget'):storage_guard(tmp_path,max_output_gib=10/1024**3)
