variable "prefix" {
  description = "Resource name prefix"
  type        = string
}

variable "step_function_arn" {
  description = "ARN of the Step Function to invoke"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the SQS queue to trigger Lambda"
  type        = string
}
