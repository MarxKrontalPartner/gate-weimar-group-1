
# Gate Weimar

A Python-based message broker system for managing data streams and communication between services.

## Features

- Message producer and consumer components
- Docker-based broker infrastructure

## Getting Started

### Prerequisites

- Docker & Docker Compose

### Installation

```bash
# Clone the repository
git clone https://github.com/username/gate-weimar.git

# Navigate to the project directory
cd gate-weimar

# Install Python dependencies (first time usage)
poetry install

# Start the Python environment
poetry shell

# Start the broker infrastructure (make sure docker is running)
cd gate_weimar/broker
docker-compose up -d

# Return to base folder
cd ..
```

### Usage

```bash
# Start the producer
poetry shell
python producer.py

# Start the consumer (in another terminal)
poetry shell
python consumer.py
```
