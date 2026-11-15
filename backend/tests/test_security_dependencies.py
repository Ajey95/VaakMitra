from pathlib import Path


def test_jwt_dependency_does_not_ship_unused_python_ecdsa():
    requirements = (Path(__file__).parents[1] / "requirements-core.txt").read_text(encoding="utf-8")

    assert "python-jose" not in requirements.lower()
    assert "pyjwt[crypto]" in requirements.lower()
