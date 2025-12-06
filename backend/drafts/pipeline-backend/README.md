# Pipeline Backend

A FastAPI-based data streaming orchestration engine using Kafka (Redpanda), QuixStreams, and PostgreSQL.

## 🚀 Quick Start

### 1. Prerequisites
* Docker & Docker Compose
* Python 3.12+ & Poetry
poetry env use python3.12

### 2. Setup & Run
```bash
# 1. Configure Environment
cp .env.example .env  # Ensure DB credentials match docker-compose.yml

# 2. Start Services (Postgres & API)
docker-compose up -d --build

# 3. Apply Database Migrations
docker exec -it pipeline_api poetry run alembic upgrade head

### Other commands to run in the docker exec -it pipeline_api one might find useful 
### one can auto generate schema by only udpating models
poetry run alembic revision --autogenerate -m "add_pipeline_and_tag_tables"