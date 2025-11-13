import random
import time
from datetime import datetime, timezone

from quixstreams import Application
from quixstreams.models.messages import KafkaMessage

from gate_weimar.logger import get_logger


class Producer:
    def __init__(
        self, broker_address: str, topic_name: str, n_channels: int, frequency: float
    ):
        """
        Producer class to send messages to a Kafka topic at a specified frequency.
        
        Parameters
        ----------
        broker_address : str
            The address of the message broker.
        topic_name : str
            The name of the topic to produce messages to.
        n_channels : int
            The number of channels to include in each message.
        frequency : float
            The frequency (in Hz) at which to produce messages.
        """
        # Initialize the Quix Application with the specified broker address
        self.app = Application(broker_address=broker_address)

        # Define topic
        self.topic = self.app.topic(name=topic_name)

        # Get producer from the application
        self.producer = self.app.get_producer()

        # Data generation setup
        self.n_channels = n_channels
        self.frequency = frequency
        self.interval = 1.0 / self.frequency

        # Logger setup
        self.logger = get_logger("Producer")

    def produce(self) -> None:
        """
        Start producing messages to the topic.
        """

        # Log the production details
        self._log_details()

        self._produce()

    def _produce(self) -> None:
        """
        Produce messages
        """
        while True:
            # Produce Kafka message with the current UTC timestamp
            self._produce_kafka_message()

            # Sleep for the specified interval
            time.sleep(self.interval)

    def _log_details(self):
        """
        Log the details of the message production.
        """
        self.logger.info(
            f"Producing messages to topic '{self.topic.name}' at {self.frequency} Hz with {self.n_channels} channels"
        )

    def _produce_kafka_message(self) -> None:
        """
        Produce a Kafka message with the given timestamp.
        """
        # Generate current UTC timestamp in ISO format
        iso_timestamp = datetime.now(timezone.utc).isoformat()

        # Generate Kafka message
        message = self._generate_kafka_message(timestamp=iso_timestamp)

        # Produce the message to the topic
        self.producer.produce(
            topic=self.topic.name,
            value=message.value,
            key=message.key
        )

    def _generate_kafka_message(self, timestamp: str) -> KafkaMessage:
        """
        Generate a Kafka message with the specified timestamp and key.
        """
        value = self._generate_value(timestamp=timestamp)
        kafkaMessage = self.topic.serialize(key="DefaultKey", value=value)

        return kafkaMessage

    def _generate_value(self, timestamp: str) -> dict:
        """
        Generate the value for the Kafka message.
        The value contains the timestamp and random channel data.
        """
        return {
            "Timestamp": timestamp,
            **{f"channel_{i}": random.random() for i in range(self.n_channels)},
        }

if __name__ == "__main__":
    producer = Producer(
        broker_address="localhost:19092",
        topic_name="input_topic",
        n_channels=10,
        frequency=1.0,
    )
    producer.produce()
