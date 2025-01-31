# Start from the official Python image
FROM python:3.9-slim

# Create an app directory and set it as the working directory
WORKDIR /app

# Copy requirements.txt to the container
COPY requirements.txt /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files (including app.py, templates, etc.)
COPY . /app

# Expose port 7860 (the default used on Hugging Face Spaces)
EXPOSE 7860

# Start the app with Gunicorn, listening on port 7860
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "8", "--timeout", "0"]
