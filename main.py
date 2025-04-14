from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import uuid

app = FastAPI()

# Erlaube Frontend-Zugriff lokal / remote
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für Produktion anpassen!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
RESULT_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        return JSONResponse(status_code=400, content={"error": "Nur CSV-Dateien erlaubt."})

    uid = uuid.uuid4().hex[:8]
    save_path = UPLOAD_DIR / f"{uid}_{file.filename}"
    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # TODO: Hier Scraping-Prozess starten (z. B. Subprozess oder Celery)
    result_path = RESULT_DIR / save_path.name.replace(".csv", "_result.csv")
    shutil.copy(save_path, result_path)  # Platzhalter zum Testen

    return {"result_file": result_path.name}

@app.get("/result/{filename}")
def download_result(filename: str):
    file_path = RESULT_DIR / filename
    if file_path.exists():
        return FileResponse(file_path, filename=filename)
    return JSONResponse(status_code=404, content={"error": "Datei nicht gefunden."})
