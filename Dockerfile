# BPLab Trace LIMS — Backend Dockerfile
# FastAPI + Uvicorn
FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Application code
COPY backend/ ./backend/

# Templates (DOCX report/generation templates)
COPY templates/ ./templates/

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/attachments /app/data/signatures /app/logs

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
