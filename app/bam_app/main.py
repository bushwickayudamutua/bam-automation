from fastapi import FastAPI

from bam_app.routers.api import airtable_api

app = FastAPI()
app.include_router(airtable_api.router)


@app.get("/status")
def status():
    return {"status": "ok"}
