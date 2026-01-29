import os
from pathlib import Path

# Paths inside the container
# Default to /shared if not set (though spec says /shared is hardcoded)
SHARED_DIR = Path(os.getenv("SHARED_DIR", "/shared"))

INBOX_DIR = SHARED_DIR / "inbox"
PROCESSING_DIR = SHARED_DIR / "processing"
OUTPUT_DIR = SHARED_DIR / "output"
LOGS_DIR = SHARED_DIR / "logs"

def setup_directories():
    """Ensure all required directories exist on startup."""
    print("Setting up directories...")
    for d in [INBOX_DIR, PROCESSING_DIR, OUTPUT_DIR, LOGS_DIR]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            print(f"Checked/Created: {d}")
        except Exception as e:
            print(f"Error creating {d}: {e}")
