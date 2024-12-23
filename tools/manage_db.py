import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.db_manager import DatabaseManager

def clear_database(db_path: str, backup: bool = True):
    """Clear the database with optional backup"""
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    if backup:
        # Create backup before clearing
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(
            backup_dir, 
            f"processed_videos_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        )
        
        with sqlite3.connect(db_path) as conn:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            print(f"Created backup at: {backup_path}")

    # Clear the database
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM processed_videos")
        conn.commit()
        print("Database cleared successfully")

def main():
    db_path = "data/processed_videos.db"
    
    while True:
        print("\nDatabase Management")
        print("1. View all entries")
        print("2. View statistics")
        print("3. Clear database (with backup)")
        print("4. Clear database (no backup)")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        db = DatabaseManager(db_path)
        
        if choice == '1':
            # View database contents
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM processed_videos 
                    ORDER BY processed_date DESC
                """)
                rows = cursor.fetchall()
                if rows:
                    print("\nDatabase entries:")
                    for row in rows:
                        print("\n" + "-" * 80)
                        print(f"Video ID: {row[0]}")
                        print(f"Title: {row[1]}")
                        print(f"Compilation: {row[2]}")
                        print(f"Processed: {row[3]}")
                        print(f"Uploaded: {row[4] or 'Not uploaded'}")
                        print(f"Status: {row[5] or 'Pending'}")
                else:
                    print("\nNo entries in database")
                    
        elif choice == '2':
            # View statistics
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN upload_status = 'uploaded' THEN 1 ELSE 0 END) as uploaded,
                        SUM(CASE WHEN upload_status IS NULL THEN 1 ELSE 0 END) as pending
                    FROM processed_videos
                """)
                total, uploaded, pending = cursor.fetchone()
                print("\nDatabase Statistics:")
                print(f"Total videos: {total or 0}")
                print(f"Uploaded: {uploaded or 0}")
                print(f"Pending: {pending or 0}")
                
        elif choice == '3':
            confirm = input("\nAre you sure you want to clear the database? (y/N): ").lower()
            if confirm == 'y':
                clear_database(db_path, backup=True)
            else:
                print("Operation cancelled")
                
        elif choice == '4':
            confirm = input("\nWARNING: This will permanently delete all entries without backup!\nAre you sure? (y/N): ").lower()
            if confirm == 'y':
                second_confirm = input("Type 'DELETE' to confirm: ").strip()
                if second_confirm == 'DELETE':
                    clear_database(db_path, backup=False)
                else:
                    print("Operation cancelled")
            else:
                print("Operation cancelled")
                
        elif choice == '5':
            print("\nExiting...")
            break
            
        else:
            print("\nInvalid choice")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 