# Gate Weimar Group 1 Project

This project consists of a **Vue 3 frontend** and a **Python FastAPI backend** with QuixStreams and Redpanda. The entire application can now be run using **Docker Compose**, simplifying setup and development.

---

## Table of Contents

- [Requirements](#requirements)  
- [Clone the Repository](#clone-the-repository)  
- [Running the Application](#running-the-application)  
- [Frontend Development](#frontend-development)  
- [Backend Development](#backend-development)  
- [Accessing the Application](#accessing-the-application)  
- [Stopping the Application](#stopping-the-application)  
- [Notes](#notes)  

---

## Requirements

- Docker Desktop with **Docker Compose V2**  
- Sufficient CPU and memory for Redpanda and other services  

---

## Clone the Repository

```bash
git clone https://github.com/MarxKrontalPartner/gate-weimar-group-1.git
cd gate-weimar-group-1/backend/drafts/pipeline-backend-lite
```

---

## Running the Application

The Docker Compose setup includes:

- **Redpanda** (Kafka-compatible streaming platform)  
- **Redpanda Console**  
- **Backend (FastAPI + QuixStreams)**  
- **Frontend (Vue 3 dev server with hot reload)**  

Start all services:

```bash
docker compose up --build
```

---

## Frontend Development

The frontend is built with **Vue 3 + Vite** and runs in development mode with hot reload.

- Node version inside container: **>= 20.19** (required for Vite 5)  
- Port exposed: **5173**

No manual `npm install` is required inside Docker — dependencies are installed during build.

To run the frontend outside Docker (optional):

```bash
cd ../../../frontend/prototype
npm install
npm run dev -- --host 0.0.0.0
```

---

## Backend Development

The backend runs **FastAPI + QuixStreams** in Docker. Logs are streamed to your terminal.

- FastAPI server port: **8000**  
- The backend depends on Redpanda to start correctly; Docker Compose ensures startup order.

Dockerfile configuration:

```dockerfile
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- `--reload` (not included in current version) would allow automatic reload during development when Python files change.

---

## Accessing the Application

- **Frontend:** [http://localhost:5173](http://localhost:5173)  
- **Backend API:** [http://localhost:8000](http://localhost:8000)  
- **Redpanda Console:** [http://localhost:8080](http://localhost:8080)

---

## Stopping the Application

```bash
docker compose down -v --remove-orphans
```

This stops all containers and removes networks created by Docker Compose.

---

## Notes

- The frontend container uses **Node.js 20** for Vite compatibility.  
- The backend container uses **Python 3.11-slim**.  
- Make sure Docker has enough resources for Redpanda, as it can be resource-intensive.  
- For development, you can mount source code to enable live reload for both frontend and backend.
