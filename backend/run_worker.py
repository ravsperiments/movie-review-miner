# run_worker.py

from redis import Redis
from rq import Worker, Queue, Connection

# Connect to Redis service by Docker container name
redis_conn = Redis(host="redis", port=6379)

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker(["default"])
        worker.work()
