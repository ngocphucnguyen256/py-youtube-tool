import logging
from datetime import datetime
import os

def setup_logger():
    log_file = f"logs/youtube_reup_{datetime.now():%Y%m%d_%H%M%S}.log"
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__) 