from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os
import uuid
import shutil
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from extractors.passport_extractor import PassportExtractor

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Document Form Filler API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

# Document detection patterns
PASSPORT_PATTERNS = [
    r'passport',
    r'travel\s+document',
    r'p\d{8,9}',  # Passport number pattern
    r'nationality',
    r'date\s+of\s+birth',
    r'mrz'  # Machine readable zone
]

G28_PATTERNS = [
    r'g-?28',
    r'notice\s+of\s+entry\s+of\s+appearance',
    r'attorney\s+or\s+representative',
    r'bar\s+number',
    r'law\s+firm',
    r'accreditation'
]

# Helper Functions
def detect_document_type(filename: str, content: bytes = None) -> Optional[str]:
    """Detect document type based on filename and content"""
    filename_lower = filename.lower()
    
    # Simple filename-based detection
    if any(pattern in filename_lower for pattern in ['passport']):
        return 'passport'
    elif any(pattern in filename_lower for pattern in ['g28', 'g-28']):
        return 'g28'
    
    # If content analysis is needed, it would go here
    # For Phase 2, we'll stick to filename detection
    
    return None

def save_uploaded_file(session_id: str, file: UploadFile, doc_type: str = None) -> str:
    """Save uploaded file to session directory"""
    session_dir = UPLOADS_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    # Generate filename
    if doc_type:
        file_extension = Path(file.filename).suffix
        filename = f"{doc_type}{file_extension}"
    else:
        filename = file.filename
    
    file_path = session_dir / filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return str(file_path)

# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Document Form Filler API"}

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """Upload and process document file"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
        
        # Reset file pointer
        await file.seek(0)
        
        # Detect document type
        doc_type = detect_document_type(file.filename, file_content)
        
        # Save file
        file_path = save_uploaded_file(session_id, file, doc_type)
        
        # Generate response
        return {
            "success": True,
            "documentType": doc_type,
            "fileName": file.filename,
            "fileSize": len(file_content),
            "sessionId": session_id,
            "filePath": file_path,
            "previewUrl": f"/api/preview/{session_id}/{Path(file_path).name}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/preview/{session_id}/{filename}")
async def get_file_preview(session_id: str, filename: str):
    """Get file preview"""
    try:
        file_path = UPLOADS_DIR / session_id / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(file_path)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

@app.get("/api/session/{session_id}")
async def get_session_status(session_id: str):
    """Get session upload status"""
    try:
        session_dir = UPLOADS_DIR / session_id
        
        if not session_dir.exists():
            return {"exists": False, "files": {}}
        
        files = {}
        for file_path in session_dir.glob("*"):
            if file_path.is_file():
                doc_type = detect_document_type(file_path.name)
                files[doc_type or 'unknown'] = {
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "previewUrl": f"/api/preview/{session_id}/{file_path.name}"
                }
        
        return {"exists": True, "sessionId": session_id, "files": files}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session check failed: {str(e)}")

@app.delete("/api/session/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up session files"""
    try:
        session_dir = UPLOADS_DIR / session_id
        
        if session_dir.exists():
            shutil.rmtree(session_dir)
        
        return {"success": True, "message": "Session cleaned up"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@app.post("/api/process/{session_id}")
async def process_documents(session_id: str):
    """Process uploaded documents (placeholder for Phase 3)"""
    try:
        session_dir = UPLOADS_DIR / session_id
        
        if not session_dir.exists():
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if both documents are uploaded
        files = list(session_dir.glob("*"))
        if len(files) < 2:
            raise HTTPException(status_code=400, detail="Both passport and G-28 form required")
        
        # Simulate processing
        return {
            "success": True,
            "sessionId": session_id,
            "message": "Documents processed successfully",
            "nextStep": "extraction"  # For Phase 3
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/api/extract/passport/{session_id}")
async def extract_passport_data(session_id: str):
    """Extract data from uploaded passport"""
    try:
        session_dir = UPLOADS_DIR / session_id
        
        if not session_dir.exists():
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Find passport file
        passport_file = None
        for file_path in session_dir.glob("*"):
            if "passport" in file_path.name.lower():
                passport_file = file_path
                break
        
        if not passport_file:
            # Try to find any image/PDF file
            for file_path in session_dir.glob("*"):
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.pdf']:
                    passport_file = file_path
                    break
        
        if not passport_file:
            raise HTTPException(status_code=404, detail="Passport file not found")
        
        # Extract data
        extractor = PassportExtractor()
        result = extractor.extract(str(passport_file))
        
        # Store extraction results in session
        result['sessionId'] = session_id
        result['filename'] = passport_file.name
        
        return JSONResponse(content=result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/api/extract/passport/{session_id}")
async def get_passport_extraction(session_id: str):
    """Get previously extracted passport data"""
    try:
        # For now, re-extract on GET request
        # In production, this would retrieve cached results
        return await extract_passport_data(session_id)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get extraction: {str(e)}")

# Mount static files (this should be last)
app.mount("/", StaticFiles(directory="static", html=True), name="static")