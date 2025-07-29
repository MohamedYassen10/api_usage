import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import os
from datetime import datetime
import uuid
from typing import Optional
import pandas as pd
from starlette.middleware.cors import CORSMiddleware
from io import BytesIO

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return {"message": "Hello World"}

# Vercel requires this named variable
handler = app
# Configuration
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
@app.post("/upload-file/")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df = pd.read_excel(BytesIO(content), engine="openpyxl")
        return {
            "columns": list(df.columns),
            "sample_data": df.head().to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(500, f"Error reading file: {str(e)}")

@app.get("/download-file/{file_id}")
async def download_file(file_id: str):
    try:
        # Find file by ID (in production, use database lookup)
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(file_id):
                file_path = os.path.join(UPLOAD_DIR, filename)

                # For Excel files, ensure proper content type
                if filename.lower().endswith('.xlsx'):
                    return FileResponse(
                        path=file_path,
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        filename=filename[len(file_id):]  # Original extension
                    )
                else:
                    return FileResponse(
                        path=file_path,
                        filename=filename[len(file_id):]
                    )

        raise HTTPException(404, "File not found")
    except Exception as e:
        raise HTTPException(500, f"Error serving file: {str(e)}")


@app.get("/download-excel/{file_id}")
async def download_excel(file_id: str):
    """Special endpoint specifically for Excel files with proper headers for SSIS"""
    try:
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(file_id):
                file_path = os.path.join(UPLOAD_DIR, filename)

                if not filename.lower().endswith('.xlsx'):
                    raise HTTPException(400, "Requested file is not an Excel file")

                # Use StreamingResponse for large files
                def iterfile():
                    with open(file_path, mode="rb") as file_like:
                        yield from file_like

                return StreamingResponse(
                    iterfile(),
                    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={
                        "Content-Disposition": f"attachment; filename={filename[len(file_id):]}",
                        "Access-Control-Expose-Headers": "Content-Disposition"
                    }
                )

        raise HTTPException(404, "File not found")
    except Exception as e:
        raise HTTPException(500, f"Error serving file: {str(e)}")


@app.get("/list-files/")
async def list_files():
    return {
        "files": [
            {
                "id": f.split("_")[0],
                "name": f,
                "size": os.path.getsize(os.path.join(UPLOAD_DIR, f))
            }
            for f in os.listdir(UPLOAD_DIR)
        ]
    }

if __name__ == "__main__":
                    uvicorn.run(
                        app,
                        host=" 127.0.0.1",  # Listen on all network interfaces
                        port=63004,
                        reload=True
                    )
