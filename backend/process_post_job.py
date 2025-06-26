# backend/process_post_job.py

from rq import Queue
from redis import Redis
from tasks.save_task import save_parsed_post  # updated name
import subprocess
import json

redis_conn = Redis(host="redis", port=6379)
q = Queue(connection=redis_conn)

def process_post_job(url: str):
    """
    Runs a subprocess to parse a blog post at `url` and enqueues save_parsed_post()
    """
    try:
        print(f"[INFO] Processing post: {url}")

        process = subprocess.Popen(
            ["python", "crawler/parse_post.py", "--url", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Subprocess failed: {stderr}")
        print(f"[DEBUG] Subprocess stdout:\n{stdout}")
        print(f"[DEBUG] Subprocess stderr:\n{stderr}")

        post_data = json.loads(stdout)
        q.enqueue(save_parsed_post, post_data)
        print(f"[INFO] Enqueued save for: {post_data['title'][:50]}")

    except Exception as e:
        print(f"[ERROR] Failed to process {url}: {e}", flush=True)
        with open("failed_links.txt", "a") as f:
            f.write(f"[post_job_error] {url} error: {e}\n")
