from fastapi import FastAPI

app = FastAPI(title="SmartBin API")


@app.get("/api/health")
def health():
    return {"status": "ok"}
