import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
QUEUES = ["emails", 'default']