"""Offline-first SQLite storage for edge deployment."""
import sqlite3
import os
from datetime import datetime

class EdgeStorageManager:
    """Manages local SQLite database to ensure raw audio privacy and offline capability."""
    
    def __init__(self):
        # Database sits locally on the edge device
        self.db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'edge_local.db')
        self._initialize_schema()
        
    def _initialize_schema(self):
        """Creates the local tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS therapy_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id TEXT NOT NULL,
                target_phoneme TEXT NOT NULL,
                gop_score REAL,
                vsa_area REAL,
                timestamp TEXT NOT NULL,
                is_synced INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def save_session(self, child_id: str, target: str, metrics: dict) -> bool:
        """
        Saves mathematical metrics to local disk.
        Raw audio is explicitly NOT saved to maintain pediatric privacy.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO therapy_sessions (child_id, target_phoneme, gop_score, vsa_area, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                child_id,
                target,
                metrics.get('gop_score', 0.0),
                metrics.get('vsa_area', 0.0),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            print(f"🔒 Edge Data Secured: Session for {target} saved locally. Audio purged.")
            return True
        except Exception as e:
            print(f"Edge Storage Error: {e}")
            return False

# Global instance
edge_storage = EdgeStorageManager()
