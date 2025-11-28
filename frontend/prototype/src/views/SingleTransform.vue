<script setup lang="ts">
import { reactive } from 'vue'
import { CodeEditor } from 'monaco-editor-vue3'

const editorOptions = {
  fontSize: 14,
  minimap: { enabled: false },
  automaticLayout: true,
}

const form = reactive({
  broker_address: 'localhost:19092',
  input_topic_name: 'input_topic',
  output_topic_name: 'output_topic',
  transformation_python_code: `def transformation(row: dict) -> dict:
    logger.info(f"before :: row :: {row}")
    for key in row:
        if key.startswith("channel_"):
            row[key] += 5
    logger.info(f"after :: row :: {row}")
    return row
  `,
})

const onSubmit = () => {
  const content = `
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


# Transformation Code
###############################################################################
${form.transformation_python_code}

###############################################################################

if __name__ == "__main__":
    logger = get_logger("main")
    consumer = Consumer(
        broker_address="${form.broker_address}",
        input_topic_name="${form.input_topic_name}",
        output_topic_name="${form.output_topic_name}",
    )
    consumer.run()

  `
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = 'consumer.py'
  link.click()

  URL.revokeObjectURL(url) // cleanup
}
</script>

<template>
  <form class="form-container" @submit.prevent="onSubmit">
    <h1 class="heading">Consumer Configs</h1>
    <label for="broker_address">Broker Address</label>
    <input type="text" id="broker_address" v-model="form.broker_address" />

    <label for="input_topic_name">Input Topic Name</label>
    <input type="text" id="input_topic_name" v-model="form.input_topic_name" />

    <label for="output_topic_name">Output Topic Name</label>
    <input type="text" id="output_topic_name" v-model="form.output_topic_name" />

    <label name="transformation_python_code">Transformation Python Code</label>
    <div id="transformation_python_code" class="code-editor-container">
      <CodeEditor
        v-model:value="form.transformation_python_code"
        language="python"
        theme="vs-dark"
        :options="editorOptions"
      />
    </div>
    <button class="submit-btn" type="submit">Download Consumer.py</button>
  </form>
</template>

<style scoped>
.form-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 600px;
  margin: 2rem auto;
  background: #1e1e2f;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

label {
  font-weight: 600;
  color: #e0e0e0;
}

input[type='text'] {
  padding: 0.6rem 0.8rem;
  border: 1px solid #3a3a4f;
  border-radius: 8px;
  background: #2a2a3b;
  color: #f0f0f0;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

input[type='text']:focus {
  border-color: #4f9dff;
  box-shadow: 0 0 0 2px rgba(79, 157, 255, 0.3);
  outline: none;
}

.submit-btn {
  margin-top: 1.5rem;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  font-weight: 600;
  padding: 0.8rem 1.5rem;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
}

.submit-btn:hover {
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  box-shadow: 0 6px 14px rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}

.submit-btn:active {
  transform: translateY(1px);
  box-shadow: 0 3px 8px rgba(59, 130, 246, 0.3);
}

.heading {
  color: #e0e0e0;
}
</style>
