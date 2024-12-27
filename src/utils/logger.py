from datetime import datetime

class Logger:
    """Custom logger that adds timestamps to messages."""
    
    @staticmethod
    def log(message: str, end: str = "\n"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}", end=end)
    
    @staticmethod
    def progress(message: str):
        """Log a progress message with timestamp, overwriting the current line."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\r[{timestamp}] {message}", end="") 