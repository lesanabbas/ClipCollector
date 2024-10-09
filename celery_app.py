from celery import Celery
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Download
import yt_dlp

# Celery configuration
celery_app = Celery(
    'youtube_downloader',
    broker='redis://redis:6379/0',  # Redis as broker
    backend='redis://redis:6379/0'  # Redis for result storage
)

@celery_app.task(bind=True)
def download_youtube_video(self, video_url):
    session: Session = SessionLocal()
    # Fetching download task object from the database
    download_task = session.query(Download).filter_by(task_id=self.request.id).first()
    try:
        if not download_task:
            download_task = Download(task_id=self.request.id, status='pending')
            session.add(download_task)
            session.commit()

        # Generate the output filename using the task_id
        output_filename = f"{download_task.task_id}.mp4"  # Use task_id for the filename
        output_path = os.path.join('downloads', output_filename)  # Path where the file will be saved

        # yt_dlp options for downloading the video with the specified name
        ydl_opts = {
            'outtmpl': output_path,  # Set the output path directly here
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        }

        # Download the video using yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])  # Download the video

        # Update task status and file path in the database
        download_task.file_path = output_path  # Store the output path in the database
        download_task.status = 'completed'
        session.commit()

        return {'status': 'completed', 'file_path': output_path}
    except Exception as e:
        # Update task status to 'failed' in the database
        if download_task:
            download_task.status = 'failed'
            session.commit()
        return {'status': 'failed', 'error': str(e)}
    finally:
        session.close()

@celery_app.task(bind=True)
def process_task(self, data, *args, **kwargs):
    print(data)
    return "Task completed"
