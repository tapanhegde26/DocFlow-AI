output "api_id" {
  value = aws_apigatewayv2_api.api.id
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.api.api_endpoint
}

output "api_gateway_url" {
  description = "Invoke URL for API Gateway stage"
  value       = aws_apigatewayv2_stage.stage.invoke_url
}

output "authorizer_id" {
  value       = aws_apigatewayv2_authorizer.jwt.id
  description = "JWT Authorizer ID"
}

output "routes" {
  description = "Configured routes"
  value = [
    "POST ${aws_apigatewayv2_api.api.api_endpoint}/chat/query",
    "POST ${aws_apigatewayv2_api.api.api_endpoint}/chat/feedback",
    "POST ${aws_apigatewayv2_api.api.api_endpoint}/chat/audit",
    "POST ${aws_apigatewayv2_api.api.api_endpoint}/chat/log",
    "GET  ${aws_apigatewayv2_api.api.api_endpoint}/reviews/processes",
    "POST ${aws_apigatewayv2_api.api.api_endpoint}/reviews/edit",
    "POST ${aws_apigatewayv2_api.api.api_endpoint}/reviews/state",
    "POST ${aws_apigatewayv2_api.api.api_endpoint}/reviews/history",
    "GET ${aws_apigatewayv2_api.api.api_endpoint}/reviews/history/latest",
    "GET ${aws_apigatewayv2_api.api.api_endpoint}/reviews/history"
  ]
}

output "execution_arn" {
  value = aws_apigatewayv2_api.api.execution_arn
}