FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir flask gunicorn

# Make sure the folders exist
RUN mkdir -p videos static/output

# Expose port
EXPOSE 10000

# Start the app
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
