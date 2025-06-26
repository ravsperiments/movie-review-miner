from redis import Redis
from rq import Queue
from tasks.parse_post_task import parse_post_task

redis_conn = Redis(host="redis", port=6379)
q = Queue("default", connection=redis_conn)

url = "https://baradwajrangan.wordpress.com/2025/06/25/interview-ram-parandhu-po/"
job = q.enqueue(parse_post_task, url)
print(f"Enqueued job: {job.id}")
