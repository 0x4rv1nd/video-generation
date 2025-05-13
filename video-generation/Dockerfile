FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy all project files to the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary folders
RUN mkdir -p videos static/output

# Expose the port your app will run on
EXPOSE 10000

# Start the Flask app using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
