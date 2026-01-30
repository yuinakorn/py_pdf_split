import re
import shutil
from pathlib import Path
from typing import Dict, Any, List
import logging

import pdfplumber
from pypdf import PdfReader, PdfWriter
from app.core import config

# Setup a simple logger
logger = logging.getLogger("pdf_processor")
logging.basicConfig(level=logging.INFO)

# Flexible regex allowing dashes and spaces anywhere between digits
# Matches 13 digits with arbitrary spacing/dashing, e.g. "1 2 3 4..." or "1-2345..."
THAI_ID_REGEX = r"\b\d(?:\s*[-]?\s*\d){12}\b"

def extract_thai_id(text: str) -> str | None:
    """
    Extract the Thai Citizen/Tax ID.
    Prioritizes the ID associated with 'ผู้ถูกหักภาษี ณ ที่จ่าย' (Payee), 
    which typically appears after the Payer's ID in 50 Twi forms.
    """
    if not text:
        return None
        
    # Find all 13-digit sequences (with spaces/dashes)
    matches = list(re.finditer(THAI_ID_REGEX, text))
    valid_ids = []
    
    for match in matches:
        raw_id = match.group(0)
        clean_id = re.sub(r"[\s-]", "", raw_id)
        if len(clean_id) == 13:
            valid_ids.append((match.start(), clean_id))
            
    if not valid_ids:
        return None
        
    # Strategy 1: Look for "ผู้ถูกหักภาษี" (Payee) keyword
    # We want the first ID *after* this keyword.
    keyword = "ผู้ถูกหักภาษี"
    idx = text.find(keyword)
    
    if idx != -1:
        for start_pos, clean_id in valid_ids:
            if start_pos > idx:
                return clean_id
                
    # Strategy 2: Fallback - If there are multiple IDs, usually the second one is the payee
    # (First is Payer, Second is Payee)
    if len(valid_ids) >= 2:
        return valid_ids[1][1]
        
    # Strategy 3: Default to the first found if only one exists or logic fails
    return valid_ids[0][1]

def extract_year_from_job_id(job_id: str) -> str:
    """
    Extract a 4-digit year from the job_id (e.g. 'tax-2568-1' -> '2568').
    Defaults to 'unknown_year' if not found.
    """
    # Look for 25xx first (Thai year assumption based on context), or just any 4 digits
    # Simple regex for 4 digits
    match = re.search(r"(\d{4})", job_id)
    if match:
        return match.group(1)
    return "unknown_year"

def process_pdf_job(job_id: str) -> Dict[str, Any]:
    input_file = config.INBOX_DIR / f"{job_id}.pdf"
    
    # Extract year and determine output directory
    year = extract_year_from_job_id(job_id)
    output_job_dir = config.OUTPUT_DIR / year
    
    if not input_file.exists():
        msg = f"File not found: {input_file}"
        logger.error(msg)
        return {"jobId": job_id, "status": "failed", "error": msg}
    
    # Create output directory for this year (shared by all jobs in this year)
    output_job_dir.mkdir(parents=True, exist_ok=True)
    
    # Note: We do NOT remove the directory here anymore because it contains files for other users/jobs.
    # We will overwrite individual files as we process them.
    
    created_files = []
    page_ids = [] # Store (page_index, citizen_id)
    
    try:
        # Step 1: Extract Text & IDs using pdfplumber
        logger.info(f"Scanning text in {input_file}")
        with pdfplumber.open(input_file) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                cid = extract_thai_id(text)
                page_ids.append(cid if cid else "unknown")
                
        # Step 2: Split and Save using pypdf
        logger.info(f"Splitting files for {job_id}")
        reader = PdfReader(input_file)
        
        # Determine total pages from reader to be safe (should match plumber)
        total_pages = len(reader.pages)
        
        for i, page in enumerate(reader.pages):
            writer = PdfWriter()
            writer.add_page(page)
            
            # Get ID from Step 1
            citizen_id = page_ids[i] if i < len(page_ids) else "unknown"
            
            # Determine filename
            filename = f"{citizen_id}.pdf"
            
            # Check for duplicates in this job batch to avoid overwriting or confusion
            # If we have multiple pages for same person, spec says "แยก PDF ทีละหน้า" -> implying separate files.
            # We append _{page_number+1} if it is a duplicate or just generic safety?
            # Let's check existence using path
            file_path = output_job_dir / filename
            # Modification: Always overwrite existing files.
            # Previously:
            # if file_path.exists():
            #     filename = f"{citizen_id}_{i+1}.pdf"
            #     file_path = output_job_dir / filename
            
            with open(file_path, "wb") as out_f:
                writer.write(out_f)
            
            created_files.append(filename)
            
        return {
            "jobId": job_id,
            "pageCount": total_pages,
            "createdFiles": created_files,
            "status": "success"
        }

    except Exception as e:
        logger.exception(f"Error processing job {job_id}")
        return {
            "jobId": job_id,
            "status": "failed",
            "error": str(e),
            "createdFiles": created_files # Return partial
        }

def cleanup_output_directory(year: str) -> bool:
    """
    Clears the output directory for a specific year.
    Returns True if directory existed and was deleted, False otherwise.
    """
    year_dir = config.OUTPUT_DIR / year
    if year_dir.exists():
        try:
            shutil.rmtree(year_dir)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {year_dir}: {e}")
            return False
    return False

def list_inbox_files() -> List[str]:
    """
    List all PDF files in the inbox directory.
    """
    if not config.INBOX_DIR.exists():
        return []
    return [f.name for f in config.INBOX_DIR.glob("*.pdf")]

def delete_inbox_file(filename: str) -> bool:
    """
    Delete a specific file from the inbox directory.
    """
    file_path = config.INBOX_DIR / filename
    if file_path.exists() and file_path.is_file():
        try:
            file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete inbox file {filename}: {e}")
            return False
    return False

def list_output_files(year: str) -> List[str]:
    """
    List all PDF files in the output directory for a specific year.
    """
    year_dir = config.OUTPUT_DIR / year
    if not year_dir.exists():
        return []
    return [f.name for f in year_dir.glob("*.pdf")]

def list_output_years() -> List[str]:
    """
    List all year directories in the output folder.
    """
    if not config.OUTPUT_DIR.exists():
        return []
    # Filter only directories
    return [d.name for d in config.OUTPUT_DIR.iterdir() if d.is_dir()]
    return False

