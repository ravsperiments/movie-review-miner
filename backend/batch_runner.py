import os
import math
import subprocess
import json

from utils.logger import get_logger

BATCH_SIZE = 50
INPUT_FILE = "all_blog_links.json"

with open(INPUT_FILE, "r") as f:
    all_links = json.load(f)

total = len(all_links)
batches = math.ceil(total / BATCH_SIZE)

logger = get_logger(__name__)
logger.info("Total posts: %s | Running %s batches of %s each", total, batches, BATCH_SIZE)

for i in range(batches):
    start = i * BATCH_SIZE
    end = min(start + BATCH_SIZE, total)
    logger.info("Processing batch %s/%s (posts %s to %s)", i + 1, batches, start, end)
    
    result = subprocess.run([
        "python", "extract_post_content.py",
        "--start", str(start),
        "--end", str(end)
    ])

    if result.returncode != 0:
        logger.error("Batch %s failed with return code %s", i + 1, result.returncode)
        break
