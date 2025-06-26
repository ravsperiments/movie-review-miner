import os
import math
import subprocess
import json

BATCH_SIZE = 50
INPUT_FILE = "all_blog_links.json"

with open(INPUT_FILE, "r") as f:
    all_links = json.load(f)

total = len(all_links)
batches = math.ceil(total / BATCH_SIZE)

print(f"📦 Total posts: {total} | Running {batches} batches of {BATCH_SIZE} each...")

for i in range(batches):
    start = i * BATCH_SIZE
    end = min(start + BATCH_SIZE, total)
    print(f"🚀 Processing batch {i+1}/{batches} (posts {start} to {end})")
    
    result = subprocess.run([
        "python", "extract_post_content.py",
        "--start", str(start),
        "--end", str(end)
    ])

    if result.returncode != 0:
        print(f"❌ Batch {i+1} failed with return code {result.returncode}")
        break
