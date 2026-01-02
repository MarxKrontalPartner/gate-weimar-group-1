export interface Payload {
  pipeline_id: string
  input_topic: string
  output_topic: string
  transformations: string[]
  allow_producer: boolean
  n_channels: number
  frequency: number
}
