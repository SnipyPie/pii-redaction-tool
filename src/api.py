import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from .redactor import process_file
from .detectors import CATEGORIES

app = FastAPI(title="PII Redaction API")

def cleanup_file(path: str | Path) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/redact")
async def redact_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
    # We use delete=False to pass paths across functions and ultimately to FileResponse.
    # We enqueue a background task to safely delete these files after the response is sent.
    input_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    output_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    audit_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    
    input_path = Path(input_temp.name)
    output_path = Path(output_temp.name)
    audit_path = Path(audit_temp.name)
    
    try:
        input_temp.write(content)
        input_temp.close()
        output_temp.close()
        audit_temp.close()
        
        process_file(
            input_path=input_path,
            output_path=output_path,
            audit_path=audit_path,
            categories=set(CATEGORIES),
            dry_run=False
        )
        
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        background_tasks.add_task(cleanup_file, audit_path)
        
        return FileResponse(
            path=output_path,
            filename=f"redacted_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except ValueError as e:
        cleanup_file(input_path)
        cleanup_file(output_path)
        cleanup_file(audit_path)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        cleanup_file(input_path)
        cleanup_file(output_path)
        cleanup_file(audit_path)
        raise HTTPException(status_code=500, detail="Internal server error during document processing.")
