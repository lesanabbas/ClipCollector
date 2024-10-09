from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
from celery_app import download_youtube_video, celery_app
from fastapi.responses import FileResponse
import os
from models import Download
from database import SessionLocal
from sqlalchemy.orm import Session
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Set the base directory for downloads
BASE_DIR = os.getcwd()

# Define Pydantic model for request body
class YouTubeURLRequest(BaseModel):
    youtube_url: str

# This function will take the YouTube URL from request body and send it to the Celery worker
@app.post("/download/")
async def download_video(request: YouTubeURLRequest):
    task = download_youtube_video.delay(request.youtube_url)
    return {"task_id": task.id}

# This API will check the status of the task by task_id
@app.get("/status/{task_id}")
def get_status(task_id: str):
    session: Session = SessionLocal()
    try:
        download_task = session.query(Download).filter_by(task_id=task_id).first()
        if not download_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "task_id": task_id,
            "status": download_task.status,
            "file_path": download_task.file_path if download_task.status == 'completed' else None
        }
    finally:
        session.close()

@app.get("/download/{task_id}")
def download_file(task_id: str):
    session: Session = SessionLocal()
    try:
        download_task = session.query(Download).filter_by(task_id=task_id).first()
        if not download_task:
            raise HTTPException(status_code=404, detail="Task not found")
        if download_task.status != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")

        # Construct the full file path
        file_path = os.path.join(BASE_DIR, download_task.file_path)
        
        logging.info(f"Checking file at: {file_path}")

        if os.path.exists(file_path):  # Ensure the file exists on disk
            # Update the `is_downloaded` field in the database to True
            download_task.is_downloaded = True

            # Attempt to commit the change
            try:
                session.commit()
                logging.info("Updated is_downloaded to True in the database.")
            except Exception as commit_exception:
                logging.error(f"Failed to commit changes: {commit_exception}")
                raise HTTPException(status_code=500, detail="Internal server error while updating download status")

            return FileResponse(
                path=file_path, 
                media_type='application/octet-stream', 
                filename=os.path.basename(file_path)
            )
        else:
            raise HTTPException(status_code=404, detail="File not found on server")

    finally:
        session.close()
        
        
def cleanup_downloaded_files():
    session: Session = SessionLocal()
    try:
        # Query for all downloaded files
        downloaded_files = session.query(Download).filter_by(is_downloaded=True).all()

        for download in downloaded_files:
            file_path = download.file_path
            
            # Check if the file exists before trying to delete
            if os.path.exists(file_path):
                os.remove(file_path)  # Delete the file
                logging.info(f"Deleted file: {file_path}")

            # Delete the record from the database
            session.delete(download)
        
        session.commit()  # Commit the transaction
    except Exception as e:
        logging.error(f"Error during cleanup: {str(e)}")
    finally:
        session.close()