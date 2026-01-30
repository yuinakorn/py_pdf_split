from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from typing import Dict, Any, List

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
    Check status of a job.
    Since output is now grouped by year, we check if the Year folder exists.
    """
    # 1. Extract Year
    year = pdf_service.extract_year_from_job_id(job_id)
    output_year_dir = config.OUTPUT_DIR / year
    
    # 2. Check Input existence (to verify job validity)
    input_file = config.INBOX_DIR / f"{job_id}.pdf"
    
    # 3. Logic:
    # If Output Year Dir exists -> We assume 'completed' (loose check)
    # If not, but Input exists -> 'pending'
    # Neither -> 'not found'
    
    if output_year_dir.exists():
        # Count total files in that year as a stat
        # Note: This is NOT the count for this specific job, but for the whole year.
        files = [f.name for f in output_year_dir.glob("*.pdf")]
        return {
            "jobId": job_id,
            "status": "completed", 
            "message": "Year directory exists. Files are merged.",
            "year": year,
            "totalFilesInYear": len(files)
        }
    
    if input_file.exists():
        return {"jobId": job_id, "status": "pending"}
        
    raise HTTPException(status_code=404, detail="Job not found")

@router.delete("/output/{year}", tags=["Maintenance"])
async def clear_output_directory_by_year(year: str) -> Dict[str, Any]:
    """
    Clear all files in the output directory for a specific fiscal year.
    """
    success = pdf_service.cleanup_output_directory(year)
    if success:
        return {"status": "success", "message": f"Output directory for year {year} cleared"}
    else:
        # It's not necessarily an error if it didn't exist, but we can report it.
        return {"status": "not_found", "message": f"Directory for year {year} not found or already empty"}

@router.get("/inbox", tags=["Inbox"])
async def list_inbox_files() -> List[str]:
    """
    List all PDF files currently in the inbox.
    """
    return pdf_service.list_inbox_files()

@router.delete("/inbox/{filename}", tags=["Inbox"])
async def delete_inbox_file(filename: str) -> Dict[str, Any]:
    """
    Delete a specific file from the inbox.
    """
    success = pdf_service.delete_inbox_file(filename)
    if success:
        return {"status": "success", "message": f"File {filename} deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found or could not be deleted")

@router.get("/output/{year}", tags=["Retrieval"])
async def list_output_files(year: str) -> List[str]:
    """
    List all processed PDF files for a specific year.
    """
    return pdf_service.list_output_files(year)

@router.get("/output", tags=["Retrieval"])
async def list_output_years() -> List[str]:
    """
    List all fiscal years (subdirectories) available in the output directory.
    """
    return pdf_service.list_output_years()
