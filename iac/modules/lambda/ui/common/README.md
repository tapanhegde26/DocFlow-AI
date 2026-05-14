# Shared Lambda Services

The Shared Services lambda-based REST API provides reusable functionality for AWS-integrated services in the AI-Knowledgebase project. It is designed to support:

  *	Centralized logging to CloudWatch and OpenSearch
  *	Audit data ingestion and retrieval from PostgreSQL (RDS)
  *	Data gathering from Amazon S3 and PostgreSQL
  *	Standardized API structure for consistent local and cloud execution

The Lambda is containerized using Docker and designed to run both:
  *	In AWS Lambda behind API Gateway
  *	Locally using AWS Systems Manager Session Manager with secure port forwarding

## Key Features
  *	Python 3.13 runtime
  *	Common [app.py](./src/app.py) Lambda entrypoint
  *	Built-in routing for:
    * /audit — insert user audit records into RDS
    * /data — fetch data from RDS or S3
    * /log — push logs to CloudWatch or OpenSearch
  *	Secure secrets management via AWS Systems Manager Parameter Store and AWS Secrets Manager
  *	Designed for extensibility — additional routes, logging backends, or data sources can be added


## Usage

This Lambda is meant to be imported or reused across multiple services that need standardized logging, audit trails, or data queries within a secure, serverless architecture.

## Deploying to AWS

There are two steps to deploy a Dockerized Lambda application to AWS



This step is outside of Terraform - Terraform does not

## Running Lambda Locally with RDS Access via SSM Port Forwarding

This guide shows how to run the containerized Lambda locally, and securely connect to an RDS instance that does not have public access, using AWS Systems Manager (SSM) with port forwarding through an EC2 instance.


### Prerequisites
1. Docker installed and running
2. AWS CLI and Session Manager Plugin

```
brew install awscli
brew install --cask session-manager-plugin
```

3. Set up an EC2 instance to connect to your RDS database instance. Ensure that the EC2 has the following installed:
* Running in the same VPC/subnet as your RDS instance
* Has SSM agent installed and running
* Attached IAM role includes AmazonSSMManagedInstanceCore
4. Configure your AWS CLI profile and then start a SSM sessions.
5. You should now have:
* EC2 Instance ID
* RDS Private Endpoint
* RDS DB name, user, and password


### Configuration for Port Forwarding
1. Update [postgres_client.py](./src/shared/services/postgres_client.py) change:
* port to 5432
* host to "host.docker.internal" - host.docker.internal allows Docker to connect to localhost on your machine.
2. Start port forwarding with SSM

```
aws ssm start-session \
  --target i-xxxxxxxxxxxxxxxxx \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["your-rds-private-endpoint.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["5432"]}' \
  --profile TSH_Industries_Admin

```

  * Replace i-xxxxxxxxxxx with your EC2 instance ID
  *	Keep this session open in a terminal
  *	It securely tunnels traffic from your localhost:5432 to the RDS instance  

3. Build the Docker image
```
docker build -t xxxxxxxxxx .  - replace xxxxxxxxxx with the name you want to give your Docker image
```
4. Run the Lambda locally
```
docker run -rm -p 9000:8080 --env-file .env xxxxxxxxxx
```
5. Invoke the Lambda endpoints using curl
```
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations
  -H "Content-Type: application/json"
  -d '{
        "path": "/audit",
        "httpMethod": "POST",
        "body": "{"user_id": "u123", "client_name": "client_xyz", "app_name": "chat", "ip_address": "192.168.1.50", "user_agent": "Mozilla/5.0"}"
      }'
```

#### Notes
- Keep the SSM session terminal open while testing
- You can edit postgres_client.py to use environment variables for full portability.


#### Deployment Considerations
- Switch from hardcoded variables to Parameter Store + Secrets Manager
- Replace host.docker.internal with the real RDS endpoint (accessed inside a VPC)
