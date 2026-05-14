terraform {
  required_version = ">= 1.4.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  api_name = "${var.prefix}-ui"
  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
  safe_stage_name = var.stage_name == "$default" ? "default" : var.stage_name
}

# --- CloudWatch Log Group for API access logs
resource "aws_cloudwatch_log_group" "http_api_access" {
  name              = "/aws/apigwv2/${var.prefix}-${local.safe_stage_name}/access"
  retention_in_days = 14
  tags              = local.tags
}

# --- APIGateway HTTP API v2
resource "aws_apigatewayv2_api" "api" {
  name          = "${var.prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins =  [
      "http://forge.dev.tsh-industries.cloud",
      "https://d23q3tbo1lzod4.cloudfront.net", #uidev review ui
      "https://d2bfbx4u6813v9.cloudfront.net", #uidev chat ui
      "https://d3mpfahyci322k.cloudfront.net",
      "https://forge.dev.tsh-industries.cloud",
      "https://d2xgx1e5j6j4yv.cloudfront.net", #rev workspace chat ui
      "https://d1xd5vmztjiv6m.cloudfront.net"  #rev workspace chat ui
    ]
    allow_methods = ["GET", "POST", "PUT", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
    expose_headers = []
    max_age = 300
  }

  tags = local.tags
}

# --- JWT Authorizer
resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id          = aws_apigatewayv2_api.api.id
  name            = "${local.api_name}-jwt"
  authorizer_type = "JWT"

  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = ["account"]
    issuer   = "https://auth.tsh-industries.cloud/realms/master"
  }
}

# --- Integrations
resource "aws_apigatewayv2_integration" "chat" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.chat_lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "review" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.review_lambda_invoke_arn
  payload_format_version = "2.0"
}

# --- API Routes
# Chat
resource "aws_apigatewayv2_route" "chat_query" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /chat/query"
  target             = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "chat_feedback" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /chat/feedback"
  target             = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "chat_update_feedback" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "PUT /chat/feedback"
  target             = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "chat_audit" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /chat/audit"
  target             = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "chat_log" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /chat/log"
  target             = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "chat_signedUrl" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /chat/signed-url"
  target             = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

# Review
resource "aws_apigatewayv2_route" "reviews_processes_content" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /reviews/content"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "reviews_processes" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "GET /reviews/processes"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}


resource "aws_apigatewayv2_route" "reviews_edit" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /reviews/edit"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "reviews_state" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /reviews/state"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "reviews_history" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /reviews/history"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "reviews_history_latest" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "GET /reviews/history/latest"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "get_reviews_history" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "GET /reviews/history"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "review_audit" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /reviews/audit"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "review_log" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /reviews/log"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "reviews_signedUrl" {
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = "POST /reviews/signed-url"
  target             = "integrations/${aws_apigatewayv2_integration.review.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_stage" "stage" {
  api_id        = aws_apigatewayv2_api.api.id
  name          = var.stage_name
  #deployment_id = aws_apigatewayv2_deployment.deployment.id
  auto_deploy   = true
  tags          = local.tags

  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 100
    logging_level          = "INFO"
    data_trace_enabled     = true
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.http_api_access.arn
    format = jsonencode({
      requestId     = "$context.requestId",
      routeKey      = "$context.routeKey",
      status        = "$context.status",
      ip            = "$context.identity.sourceIp",
      userAgent     = "$context.identity.userAgent",
      jwt_sub       = "$context.authorizer.jwt.claims.sub",
      auth_error    = "$context.authorizer.error",
      auth_integration = "$context.integration.error"
    })
  }
}

# --- Lambda permissions
resource "aws_lambda_permission" "apigw_invoke_chat" {
  statement_id  = "AllowAPIGWInvokeChat"
  action        = "lambda:InvokeFunction"
  function_name = var.chat_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_invoke_review" {
  statement_id  = "AllowAPIGWInvokeReview"
  action        = "lambda:InvokeFunction"
  function_name = var.review_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
