import os
import sqlite3
from datetime import datetime

def view_database(db_path="data/processed_videos.db"):
    """Display contents of the video processing database"""
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    with sqlite3.connect(db_path) as conn:
        # Get all videos
        cursor = conn.execute("""
            SELECT 
                video_id,
                title,
                compilation_path,
                processed_date,
                uploaded_date,
                upload_status
            FROM processed_videos
            ORDER BY processed_date DESC
        """)
        
        rows = cursor.fetchall()
        if not rows:
            print("\nNo videos in database")
            return
        
        # Print statistics
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN upload_status = 'uploaded' THEN 1 ELSE 0 END) as uploaded,
                SUM(CASE WHEN upload_status IS NULL THEN 1 ELSE 0 END) as pending
            FROM processed_videos
        """)
        total, uploaded, pending = cursor.fetchone()
        
        print("\n=== Database Statistics ===")
        print(f"Total videos: {total}")
        print(f"Uploaded: {uploaded}")
        print(f"Pending: {pending}")
        
        print("\n=== Video Details ===")
        for row in rows:
            print("\n" + "-" * 80)
            print(f"Video ID: {row[0]}")
            print(f"Title: {row[1]}")
            print(f"Compilation: {row[2]}")
            print(f"Processed: {row[3]}")
            print(f"Uploaded: {row[4] or 'Not uploaded'}")
            print(f"Status: {row[5] or 'Pending'}")

if __name__ == "__main__":
    view_database() 