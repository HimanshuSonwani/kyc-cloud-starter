import os, json, time, random
import redis

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is required")

# Let redis-py parse rediss:// and set SSL automatically. No extra kwargs.
r = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=10,
    health_check_interval=30,
)

print("Worker started. Waiting for jobs…")

def process(job_id: str):
    # simulate your work
    time.sleep(2)
    score = random.randint(60, 99)
    fields = {"full_name": "Jane Doe", "dob": "1995-05-05", "document_number": "ABC1234567"}
    r.hset(f"ver:{job_id}", mapping={
        "status": "approved" if score >= 80 else "review",
        "score": str(score),
        "fields": json.dumps(fields)
    })

def main_loop():
    while True:
        # Block up to 10s for next job (prevents tight loops)
        item = r.brpop("jobs", timeout=10)  # returns (key, job_id) or None
        if not item:
            continue
        _, job_id = item
        try:
            r.hset(f"ver:{job_id}", "status", "processing")
            process(job_id)
        except Exception as e:
            r.hset(f"ver:{job_id}", mapping={"status": "error", "score": "", "fields": ""})
            print(f"Job {job_id} failed: {e}")

if __name__ == "__main__":
    main_loop()
