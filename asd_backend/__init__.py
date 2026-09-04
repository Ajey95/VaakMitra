"""
ASD-Edge-ST 2.0 — Member 3 Backend
====================================
Session orchestration, adaptive logic, encrypted local database,
privacy-safe sync, and Unity integration API.

Package layout
--------------
asd_backend/
  config.py          — centralised settings (env-driven)
  main.py            — FastAPI application entry-point
  session/           — M3.1 session orchestrator + Unity API
  adaptive/          — M3.2 adaptive dialogue/exercise engine
  db/                — M3.3 encrypted local DB, ORM, migrations
  sync/              — M3.4 metric sync + therapist backend API
"""

__version__ = "2.0.0"
