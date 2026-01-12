FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY producer/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY producer/app ./app
COPY shared/logger ./shared/logger
COPY shared/events ./shared/events

CMD ["python", "-m", "app.producer"]