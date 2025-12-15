export interface Payload {
  input_topic: string
  output_topic: string
  transformations: string[]
  allow_producer: boolean
  n_channels: number
  frequency: number
}
