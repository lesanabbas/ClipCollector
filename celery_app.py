import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Download
import yt_dlp
from uuid import uuid4

def download_youtube_video(video_url):
    session: Session = SessionLocal()
    task_id = str(uuid4())
    
    # Fetching or creating the download task in the database
    download_task = session.query(Download).filter_by(task_id=task_id).first()
    try:
        if not download_task:
            download_task = Download(task_id=task_id, status='pending')
            session.add(download_task)
            session.commit()

        # Generate the output filename using the task_id
        output_filename = f"{task_id}.mp4"  # Use task_id for the filename
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

        # Generate a downloadable URL for the file
        base_url = "http://127.0.0.1:8000/download/"  # Base URL for serving downloads
        downloadable_url = f"{base_url}{output_filename}"

        return {'status': 'completed', 'file_path': downloadable_url}
    except Exception as e:
        # Update task status to 'failed' in the database
        if download_task:
            download_task.status = 'failed'
            session.commit()
        return {'status': 'failed', 'error': str(e)}
    finally:
        session.close()
