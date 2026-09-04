# Member 3 Integration Guide

## Ownership boundaries

Member 3 owns `asd_backend/session`, `adaptive`, `db`, `sync`, `contracts`,
`migrations`, and the `/api/v1` and `/therapist` APIs. Members 1 and 2 implement
the protocols in `asd_backend/contracts/services.py` in their own packages and
provide service instances during application composition.

```python
from asd_backend.session.api import init_orchestrator

init_orchestrator(
    policy=loaded_policy,
    member1=team_member_1_alignment_service,
    member2=team_member_2_scoring_service,
)
```

Member 1 returns `AlignmentResult`; Member 2 returns `ScoringResult`. Both are
strict, versioned Pydantic contracts. Unknown fields are rejected so interface
drift fails during integration instead of producing incorrect therapy output.

## Frontend contract

The frontend uses only `http://127.0.0.1:8765/api/v1`. `audio_b64` must contain
raw 16 kHz mono signed 16-bit little-endian PCM and at most 320,000 decoded
bytes. The exercise and Tamil target must match the assigned plan.

Every attempt response includes `model_version`, `dict_version`, and
`policy_version`. Interactive documentation is at `/docs`; the machine-readable
contract is `/openapi.json`.

## Merge rules

- Do not copy Member 1 or Member 2 implementation code into the orchestrator.
- Do not import teammate implementation modules from `contracts`.
- Contract changes require tests and a version change.
- Database changes require a new Alembic revision; never edit an applied one.
- Runtime `.env`, SQLite files, caches, and model binaries stay uncommitted.
- Keep frontend changes outside this backend tree.

## Verification

```powershell
python -m pip install -e ".[dev]"
python -m pytest
alembic upgrade head
python -m asd_backend.main
```
