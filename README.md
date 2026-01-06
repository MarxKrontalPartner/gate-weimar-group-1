# Gate Weimar Group 1 Project

This project is a modern data pipeline orchestrator with a **Vue 3 frontend** and a **Python FastAPI backend**. It leverages Redpanda (Kafka-compatible), QuixStreams, and Docker for dynamic, scalable streaming workflows. The entire stack is managed via **Docker Compose** for easy setup and development.

---

## Table of Contents

- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Clone the Repository](#clone-the-repository)
- [Running the Application](#running-the-application)
- [Accessing the Application](#accessing-the-application)
- [Stopping the Application](#stopping-the-application)
- [Frontend Overview](#frontend-overview)
- [Backend Overview](#backend-overview)
- [Notes](#notes)
- [Contact](#contact)

---

### Screenshots

<div style="display: flex; justify-content: space-between;">
    <img src="./frontend/prototype/docs/Sc1.png" alt="light" width="48%">
    <img src="./frontend/prototype/docs/Sc2.png" alt="dark" width="48%">
</div>

---

### Requirements

- Docker Desktop with **Docker Compose V2**
- Sufficient CPU and memory for Redpanda and other services

---

### Clone the Repository

```bash
git clone https://github.com/MarxKrontalPartner/gate-weimar-group-1.git
cd gate-weimar-group-1/
```

---

### Running the Application

The Docker Compose setup includes:

- **Redpanda** (Kafka-compatible streaming platform)
- **Redpanda Console**
- **Backend (FastAPI + Docker SDK + QuixStreams)**
- **Frontend (Vue 3 + Vite dev server)**

To build all images (build-only for worker/producer) and start all build services:

```bash
docker compose --profile build-only build
docker compose up -d --build
```

---

### Accessing the Application

- **Frontend:** [http://localhost:5173](http://localhost:5173)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Redpanda Console:** [http://localhost:8080](http://localhost:8080)

---

### Stopping the Application

```bash
docker compose down -v --remove-orphans
```

This stops all containers and removes networks created by Docker Compose.

---

### Frontend Overview

The frontend is a Vue 3 + Vite application for visually designing, running, and monitoring data pipelines.

**Features:**

- Drag-and-drop pipeline graph editor
- Code editor for Python transformations
- Real-time status/logs via WebSocket
- Multi-language UI (EN/DE)

**Development:**

- Node.js 22+ required (containerized)
- Port: 5173
- Hot reload enabled

To run the frontend outside Docker (for faster dev):

```bash
cd frontend/prototype
npm install
npm run dev -- --host 0.0.0.0
```

---

### Backend Overview

The backend is a modular FastAPI orchestration engine for data streaming pipelines. It uses Redpanda (Kafka-compatible), QuixStreams, and Docker to dynamically spawn worker and producer containers for each pipeline segment.

**Features:**

- Manager service receives pipeline definitions and spawns containers for each segment
- Worker containers execute user-defined Python transformations
- Producer containers simulate or ingest data into Kafka topics
- Shared logging and event modules for all backend services

**Tech Stack:**

- FastAPI, Docker SDK, QuixStreams, Python 3.11
- All services built as separate images and orchestrated via Docker Compose

**Development:**

- FastAPI server port: 8000
- Source code mounted for live reload
- Dynamic containers built with `build-only` profile

---

### Notes

- The frontend container uses **Node.js 22** for Vite compatibility.
- The backend containers use **Python 3.11-slim**.
- Redpanda is resource-intensive; ensure Docker has sufficient resources.
- Source code is mounted for live reload in development.
- Worker/producer containers are spawned dynamically by the backend manager.

---

## Contact

- For backend issues: Sara, Amina
- For frontend issues: Ananthu, Xavier, Victor, Thamarai
