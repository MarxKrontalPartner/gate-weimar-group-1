# Prerequisites

Docker Desktop installed and running.

# Installation
1. Build the Image (The API and the Worker(aka "consumer.py") share the same image)
```bash

docker compose build
```

2. This starts Redpanda, Redpanda Console, and the Pipeline Manager API.
```Bash

docker compose up -d
```

# Usage
1. Open Swagger UI ( http://localhost:8000/docs )

2. Use the Redpanda Console (http://localhost:8080) to create an input topic and produce a JSON message:

{"value": 10}

3. Send a POST request to /start

Sample Payload

{
  "address": "redpanda:9092",
  "input_topic": "numbers_in",
  "output_topic": "numbers_out",
  "transformations": [
    "def addNumber(row):\n    if 'value' in row:\n        row['value'] = row['value'] + 100\n    return row",
    "def mulNumber(row):\n    if 'value' in row:\n        row['value'] = row['value'] * 2\n    return row"
  ]
}

4. Check the numbers_out topic in the Console. You should see {"value": 220}
