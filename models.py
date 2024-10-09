from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class Download(Base):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, nullable=False)
    file_path = Column(String, nullable=True)  # Make file_path nullable to avoid errors
    status = Column(String, nullable=False)
    error = Column(String, nullable=True)  # Optionally store error messages
    is_downloaded = Column(Boolean, default=False)