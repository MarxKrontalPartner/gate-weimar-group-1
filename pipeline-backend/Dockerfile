FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set env variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2

# Install system dependencies (curl is needed to install poetry)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Copy only dependencies first to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create a virtualenv (Docker is already isolated)
RUN poetry config virtualenvs.create false

# Install dependencies (no root project installation yet)
RUN poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]