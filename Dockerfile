FROM python:3.9

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: Pre-download the model so it doesn't do it at runtime
# RUN python -c "from transformers import pipeline; pipeline('conversational', model='microsoft/DialoGPT-medium')"

COPY . . 

EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
