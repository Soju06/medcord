try:
    import dotenv

    dotenv.load_dotenv()
except ImportError:
    pass

import os

DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
"""Debug mode"""

MEDIA_PATH: str = os.getenv("MEDIA_PATH", "media")
"""Media path"""

IMAGE_PATH: str = os.path.join(MEDIA_PATH, "images")
"""Image path"""

DATABASE_URL: str = os.getenv("DATABASE_URL")
"""Database URL"""

DATABASE_TABLE_PREFIX: str = os.getenv("DATABASE_TABLE_PREFIX", "medcord_")
"""Database table prefix"""

PASSWORD: str = os.getenv("PASSWORD", "password")
"""Password"""

IMAGE_PROCESSING_THREAD: int = int(os.getenv("IMAGE_PROCESSING_THREAD", "8"))
"""Image processing thread"""
