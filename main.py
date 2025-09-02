from fastapi import FastAPI


app = FastAPI()

@app.get("/")
def root():
    return {
        "Project": "Nebula-Nexus"
    }