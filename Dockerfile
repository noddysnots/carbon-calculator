FROM python:3.9

# Set an environment variable so Transformers/HF Hub caches models in /tmp
ENV TRANSFORMERS_CACHE=/tmp

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# (Optional) Pre-download the model to speed up container start
# RUN python -c "from transformers import pipeline; pipeline('conversational', model='microsoft/DialoGPT-medium', cache_dir='/tmp')"

COPY . .

EXPOSE 7860

# Start with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
