import sqlite3
from datetime import datetime
from typing import List, Optional
import os

class DatabaseManager:
    def __init__(self, db_path="data/processed_videos.db"):
        self.db_path = db_path
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_videos (
                    video_id TEXT PRIMARY KEY,
                    title TEXT,
                    compilation_path TEXT,
                    processed_date TIMESTAMP,
                    uploaded_date TIMESTAMP,
                    upload_status TEXT
                )
            """)
            conn.commit()

    def add_processed_video(self, video_id: str, title: str, compilation_path: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR IGNORE INTO processed_videos 
                   (video_id, title, compilation_path, processed_date) 
                   VALUES (?, ?, ?, ?)""",
                (video_id, title, compilation_path, datetime.now())
            )
            conn.commit()

    def mark_as_uploaded(self, video_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE processed_videos SET upload_status = 'uploaded', uploaded_date = ? WHERE video_id = ?",
                (datetime.now(), video_id)
            )
            conn.commit()

    def is_video_processed(self, video_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_videos WHERE video_id = ?",
                (video_id,)
            )
            return cursor.fetchone() is not None

    def get_pending_uploads(self) -> List[tuple]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT video_id, title, compilation_path 
                   FROM processed_videos 
                   WHERE upload_status IS NULL 
                   AND compilation_path IS NOT NULL"""
            )
            return cursor.fetchall() 

    def backup_database(self):
        """Create a backup of the database"""
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = os.path.join(
            backup_dir, 
            f"processed_videos_{datetime.now():%Y%m%d_%H%M%S}.db"
        )
        
        with sqlite3.connect(self.db_path) as conn:
            backup = sqlite3.connect(backup_path)
            conn.backup(backup)
            backup.close() 

    def get_processed_video_ids(self) -> set:
        """Get all processed video IDs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT video_id FROM processed_videos")
            return set(row[0] for row in cursor.fetchall())

    def get_video_status(self, video_id: str) -> dict:
        """Get detailed status of a video"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    title,
                    compilation_path,
                    processed_date,
                    uploaded_date,
                    upload_status
                FROM processed_videos 
                WHERE video_id = ?
            """, (video_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'title': row[0],
                    'compilation_path': row[1],
                    'processed_date': row[2],
                    'uploaded_date': row[3],
                    'status': row[4] or 'pending'
                }
            return None