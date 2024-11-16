FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy only the requirements file first to leverage Docker's caching
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y ffmpeg libpq-dev && \
    apt-get clean

# Install dependencies
RUN pip install -r requirements.txt

# Copy the application code
COPY . .

# Expose the application port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
