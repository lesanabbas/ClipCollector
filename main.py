from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery_app import download_youtube_video
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
def download_video(request: YouTubeURLRequest):
    task = download_youtube_video(video_url=request.youtube_url)
    print(f"---  {task}")
    return {"task_id": task}

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/download/{task_id}")
def download_file(task_id: str):
    session: Session = SessionLocal()
    try:
        
        download_task = task_id.split(".mp4")[0]
        
        # Handle cases where the task does not exist
        if not download_task:
            logging.error(f"Download task with ID {task_id} not found.")
            raise HTTPException(status_code=404, detail="Task not found")
        
        file_path = os.path.abspath(os.path.join(BASE_DIR, f"downloads/{task_id}"))
        logging.info(f"Checking file existence at: {file_path}")

        # Check if the file exists
        if not os.path.exists(file_path):
            logging.error(f"File for task ID {task_id} not found on server at {file_path}.")
            raise HTTPException(status_code=404, detail="File not found on server")

        try:
            session.commit()
            logging.info(f"Marked task ID {task_id} as downloaded in the database.")
        except Exception as commit_exception:
            logging.error(f"Database commit failed for task ID {task_id}: {commit_exception}")
            raise HTTPException(status_code=500, detail="Error updating download status in the database")

        # Return the file as a downloadable response
        return FileResponse(
            path=file_path,
            media_type='application/octet-stream',
            filename=os.path.basename(file_path)
        )

    except HTTPException as http_exc:
        logging.error(f"HTTPException for task ID {task_id}: {http_exc.detail}")
        raise http_exc
    except Exception as exc:
        logging.error(f"Unexpected error for task ID {task_id}: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
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
