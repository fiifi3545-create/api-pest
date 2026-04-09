FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy API app
COPY pest_shield_app/requirements_api.txt /app/requirements_api.txt
RUN pip install --no-cache-dir -r /app/requirements_api.txt

COPY pest_shield_app/main.py /app/main.py

# Render sets PORT automatically
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
