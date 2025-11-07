from quixstreams import Application
import time

app = Application(broker_address="localhost:19092")
topic = app.topic("input_topic")

for i in range(5):
    topic.stream_dataframe({"channel_1": [i], "channel_2": [i*2]})
    time.sleep(1)

app.close()
