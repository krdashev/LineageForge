"""
RQ Worker entry point.

Run this as a separate process: python -m app.worker.worker
"""

from redis import Redis
from rq import Worker

from app.config import settings

if __name__ == "__main__":
    # Connect to Redis
    redis_conn = Redis.from_url(settings.redis_url)

    # Start worker
    worker = Worker(["lineageforge"], connection=redis_conn)
    print("Starting LineageForge worker...")
    worker.work()
