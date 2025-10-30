from quixstreams import Application
import uuid

from gate_weimar.logger import get_logger


class Consumer:
    def __init__(
        self, broker_address: str, input_topic_name: str, output_topic_name: str
    ):
        """
        Consumer class to read messages from an input topic, apply a transformation,
        and write the results to an output topic.

        Parameters
        ----------
        broker_address : str
            The address of the message broker.
        input_topic_name : str
            The name of the input topic to consume messages from.
        output_topic_name : str
            The name of the output topic to produce messages to.
        """
        # Set a unique consumer group to avoid conflicts
        consumer_group = f"consumer_group_{uuid.uuid4().hex[:8]}"

        # Initialize the Quix Application with the specified broker address and consumer group
        self.app = Application(
            broker_address=broker_address,
            auto_offset_reset="earliest",
            consumer_group=consumer_group,
        )

        # Define input and output topics
        self.input_topic = self.app.topic(name=input_topic_name)
        self.output_topic = self.app.topic(name=output_topic_name)

        # Create a streaming DataFrame from the input topic
        self.sdf = self.app.dataframe(self.input_topic)

        # Apply the addition function to each row in the DataFrame
        self.sdf = self.sdf.apply(transformation)

        # Send the processed DataFrame to the output topic
        self.sdf.to_topic(self.output_topic)

        # Logger setup
        self.logger = get_logger("Consumer")

    def run(self):
        """
        Start the consumer application.
        """
        self._log_details()
        self.app.run()

    def _log_details(self):
        """
        Log the details of the consumer.
        """
        self.logger.info(
            f"Consuming messages from topic '{self.input_topic.name}' and producing to topic '{self.output_topic.name}'"
        )


###############################################################################
def transformation(row: dict) -> dict:
    for key in row:
        if key.startswith("channel_"):
            row[key] += 5
    return row


###############################################################################

if __name__ == "__main__":
    consumer = Consumer(
        broker_address="localhost:19092",
        input_topic_name="input_topic",
        output_topic_name="output_topic",
    )
    consumer.run()
