from quixstreams import Application
import time
import json  # <-- import JSON

app = Application(broker_address="localhost:19092")
topic = app.topic("input_topic")

with app.get_producer() as producer:
    for i in range(5):
        data = {"channel_1": i, "channel_2": i * 2}
        producer.produce(
            topic=topic.name,
            key=str(i),
            value=json.dumps(data).encode("utf-8")  # <-- convert dict to bytes
        )
        print(f"Produced: {data}")
        time.sleep(1)


