FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manager/app ./app
COPY shared/logger ./shared/logger
COPY shared/events ./shared/events

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]