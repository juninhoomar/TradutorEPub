# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web_app.py
# Important for Flask/Gunicorn to pick up the right host
ENV PORT=5000
# Default model (can be overridden in Coolify)
ENV MODEL_NAME="google/gemini-2.0-flash-001"

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Create necessary directories for the app
RUN mkdir -p uploads translated

# Expose the port the app runs on
EXPOSE 5000

# Run the application using Gunicorn
# Using 1 worker and multiple threads because we store task state in-memory (global variable)
# If we used Redis/DB for state, we could scale workers.
# Timeout increased to 300s (5 min) for long translations
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 8 --timeout 300 web_app:app
