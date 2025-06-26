# backend/master_orchestrator.py

from rq import Queue
from redis import Redis
from tasks.parse_post_task import get_post_links_batch

import argparse

# Connect to Redis
redis_conn = Redis(host="redis", port=6379)
q = Queue(connection=redis_conn)

def main(start_page: int, end_page: int):
    for page in range(start_page, end_page + 1):
        print(f"Enqueuing get_post_links_batch for page {page}")
        q.enqueue(get_post_links_batch, page)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master orchestrator for blog post crawling.")
    parser.add_argument("--start", type=int, required=True, help="Start page number")
    parser.add_argument("--end", type=int, required=True, help="End page number")

    args = parser.parse_args()
    main(args.start, args.end)
