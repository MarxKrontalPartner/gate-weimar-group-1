# Readme.md
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

2. Create Input Topic and add Input Messages

- Option A: Open Redpanda Console ( http://localhost:8080 ), create the input topic, and produce a message like:

```{"value": 10}```

- Option B: Enable automatic topic and message generation by setting "allow_producer": true in your payload.

3. Send a POST request to /start

- Sample Payload for Option A
```Json
{
  "input_topic": "numbers_in",
  "output_topic": "numbers_out",
  "transformations": [
    "def addNumber(row):\n    if 'value' in row:\n        row['value'] = row['value'] + 100\n    return row",
    "def mulNumber(row):\n    if 'value' in row:\n        row['value'] = row['value'] * 2\n    return row"
  ]
}
```
- Sample Payload for Option B
```Json
{
  "input_topic": "input_topic",
  "output_topic": "output_topic",
  "transformations": [
    "def addNumber(row):\n    for key in row:\n        if key.startswith(\"channel_\"):\n            row[key] += 10\n    return row",
    "def mulNumber(row):\n    for key in row:\n        if key.startswith(\"channel_\"):\n            row[key] *= 2\n    return row"
  ],
  "allow_producer": true,
  "n_channels": 10,
  "frequency": 1
}
```
4. Check the numbers_out/output_topic topic in the Console. You should see the updated values upon transformation.
