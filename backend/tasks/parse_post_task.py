# backend/tasks/parse_post_task.py

from rq import Queue
from redis import Redis
from crawler.fetch_links import get_post_links
from process_post_job import process_post_job

# Optional: shared queue setup (if needed outside orchestrator)
redis_conn = Redis(host="redis", port=6379)
q = Queue(connection=redis_conn)

def get_post_links_batch(page: int):
    try:
        print(f"Fetching links for page {page}")
        links = get_post_links(page)
        print(f"Found {len(links)} links on page {page}")

        for url in links:
            print(f"Enqueuing parse_post_subprocess for {url}")
            process_post_job(url)

    except Exception as e:
        print(f"Error processing page {page}: {e}")
        # Optionally log to a file for retry
        with open("failed_links.txt", "a") as f:
            f.write(f"[page] {page} error: {e}\n")

