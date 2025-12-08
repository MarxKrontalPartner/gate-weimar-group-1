FROM python:3.11-slim

# (print statements) show up immediately in Docker Console
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy EVERYTHING in the folder (including logger.py, main.py, worker.py)

COPY . .

# Port aligned to 8000 to match docker-compose.yaml
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]