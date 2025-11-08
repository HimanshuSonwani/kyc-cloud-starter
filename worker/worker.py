import os, time, random, redis

REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL, decode_responses=True)

print("Worker listening...")
while True:
    job = r.blpop("jobs", timeout=5)
    if not job:
        continue
    _, jid = job
    print(f"Processing {jid}")
    r.hset(f"ver:{jid}", "status", "processing")
    time.sleep(2)
    score = random.randint(55, 95)
    status = "approved" if score >= 80 else ("review" if score >= 60 else "rejected")
    r.hset(f"ver:{jid}", mapping={"status": status, "score": str(score)})
    print(f"Done {jid}: {status} ({score})")
