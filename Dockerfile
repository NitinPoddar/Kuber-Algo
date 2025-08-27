# Use official Python runtime as base
FROM python:3.11-slim

# Set workdir
WORKDIR /code

# Install system deps (for psycopg2 and others)
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run Django by default (Gunicorn in prod, runserver in dev)
CMD ["gunicorn", "kuber.wsgi:application", "--bind", "0.0.0.0:8000"]
