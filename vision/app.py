from fastapi import FastAPI

app = FastAPI(title="Vision API (bootstrap)")

@app.get("/health")
def health():
    return {"ok": True, "service": "vision", "stage": "bootstrap"}
