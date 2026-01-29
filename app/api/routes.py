from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from typing import Dict, Any

from app.services import pdf_service
from app.core import config

router = APIRouter()

@router.get("/files/{year}/{cid}", tags=["Retrieval"])
async def get_employee_file(year: str, cid: str) -> Dict[str, Any]:
    """
    Check if a specific PDF file exists for an employee and return its metadata.
    """
    filename = f"{cid}.pdf"
    file_path = config.OUTPUT_DIR / year / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return {
        "status": "found",
        "year": year,
        "cid": cid,
        "filename": filename,
        "full_path": str(file_path)
    }

@router.post("/process/{job_id}", tags=["Processing"])
async def process_job(job_id: str) -> Dict[str, Any]:
    """
    Trigger processing of a PDF file identified by jobId.
    Returns the processing results synchronously.
    """
    # Simply call the synchronous service
    # Ideally should be run in threadpool if it blocks, providing async def does this automatically 
    # for synchronous calls in FastAPI (it runs in threadpool)
    result = pdf_service.process_pdf_job(job_id)
    
    if result["status"] == "failed":
        # We still return the JSON result as per spec, but maybe with 500 or 400?
        # Spec says "ส่งผลลัพธ์กลับเป็น JSON โดยประกอบด้วย... สถานะการทำงาน"
        # It doesn't strictly say HTTP status.
        # But if file not found, we should probably 404.
        if "File not found" in result.get("error", ""):
            raise HTTPException(status_code=404, detail="File not found")
        # For processing errors, we return the JSON with status=failed
        return result
        
    return result

@router.get("/status/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Check status of a job from the filesystem.
    """
    # Logic: Check if output directory exists and count files
    output_job_dir = config.OUTPUT_DIR / job_id
    
    if not output_job_dir.exists():
         # Maybe it's pending? Or never existed.
         # Check if input exists
         input_file = config.INBOX_DIR / f"{job_id}.pdf"
         if input_file.exists():
             return {"jobId": job_id, "status": "pending"}
         else:
             raise HTTPException(status_code=404, detail="Job not found")
             
    # If exists, count files
    files = [f.name for f in output_job_dir.glob("*.pdf")]
    return {
        "jobId": job_id,
        "status": "completed", # Or 'processed' since we don't track state elsewhere
        "fileCount": len(files),
        "files": files
    }

@router.delete("/output", tags=["Maintenance"])
async def clear_output_directory() -> Dict[str, str]:
    """
    Clear all files and subdirectories in the shared output directory.
    """
    pdf_service.cleanup_output_directory()
    return {"status": "success", "message": "Output directory cleared"}
