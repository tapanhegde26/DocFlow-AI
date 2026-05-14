# IaC/main.tf

terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.us_east_1]
    }

    opensearch = {
      source  = "opensearch-project/opensearch"
      version = ">= 2.2"
    }

    awscc = {
      source  = "hashicorp/awscc"
      version = "1.49.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9"
    }
  }

  required_version = ">= 1.4.0"
}

provider "aws" {
  region = "ca-central-1"
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

provider "awscc" {
  region = "ca-central-1"
}


# Create custom VPC -> Commenting for now to check xlsx flow - 'mon' workspace
/*
module "vpc" {
  source = "./modules/vpc"

  prefix      = local.common_prefix
  environment = local.environment

  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]
  enable_nat_gateway   = true
}

*/

locals {
  common_prefix   = "${terraform.workspace}-tsh-industries"
  environment     = "Development"
  #vpc_id          = module.vpc.vpc_id
  #public_subnets  = module.vpc.public_subnet_ids
  #private_subnets = module.vpc.private_subnet_ids
  #all_subnets     = concat(module.vpc.public_subnet_ids, module.vpc.private_subnet_ids)
}


module "s3_standardized_bucket" {
  source      = "./modules/s3/standardized_bucket"
  bucket_name = "${local.common_prefix}-dev-sop-standardized"
  environment = local.environment
}

module "s3_embedding_bucket" {
  source      = "./modules/s3/embedding_bucket"
  bucket_name = "${local.common_prefix}-dev-sop-embedding"
  environment = local.environment
}

module "s3_embedding_nonprocess_bucket" {
  source      = "./modules/s3/embedding_bucket_nonprocess"
  bucket_name = "${local.common_prefix}-nonprocess-sop-embedding"
  environment = local.environment
}

module "s3_raw_sop_bucket" {
  source      = "./modules/s3/raw_sop_bucket"
  bucket_name = "${local.common_prefix}-raw-sop-upload"
  environment = local.environment
}

module "s3_text_extract_bucket" {
  source      = "./modules/s3/text_extract_bucket"
  bucket_name = "${local.common_prefix}-text-extraction"
  environment = local.environment
}

module "eventbridge_data_ingestion_rule" {
  source        = "./modules/eventbridge/data_ingestion_rule"
  prefix        = local.common_prefix
  bucket_name   = module.s3_standardized_bucket.bucket_name
  sqs_queue_arn = module.sqs_data_ingestion_queue.sqs_arn
  sqs_queue_url = module.sqs_data_ingestion_queue.sqs_url
  dlq_arn       = module.sqs_data_ingestion_queue.dlq_arn
  environment   = local.environment
}

module "eventbridge_pre_formatting_rule" {
  source        = "./modules/eventbridge/pre_formatting_rule"
  prefix        = local.common_prefix
  bucket_name   = module.s3_raw_sop_bucket.bucket_name
  sqs_queue_arn = module.sqs_pre_formatting_queue.sqs_arn
  sqs_queue_url = module.sqs_pre_formatting_queue.sqs_url
  dlq_arn       = module.sqs_pre_formatting_queue.dlq_arn
  environment   = local.environment
}

module "eventbridge_vector_trigger_rule" {
  source        = "./modules/eventbridge/vector_trigger_rule"
  prefix        = local.common_prefix
  bucket_name   = module.s3_standardized_bucket.bucket_name
  sqs_queue_arn = module.sqs_vector_queue.sqs_arn
  sqs_queue_url = module.sqs_vector_queue.sqs_url
  dlq_arn       = module.sqs_vector_queue.dlq_arn
  environment   = local.environment
}

module "eventbridge_vector_trigger_nonprocess_rule" {
  source        = "./modules/eventbridge/vector_trigger_nonprocess_rule"
  prefix        = local.common_prefix
  bucket_name   = module.s3_text_extract_bucket.bucket_name
  sqs_queue_arn = module.sqs_vector_nonprocess_queue.sqs_arn
  sqs_queue_url = module.sqs_vector_nonprocess_queue.sqs_url
  dlq_arn       = module.sqs_vector_nonprocess_queue.dlq_arn
  environment   = local.environment
}

module "sqs_pre_formatting_queue" {
  source        = "./modules/sqs/pre_formatting_queue"
  prefix        = local.common_prefix
  environment   = local.common_prefix
  s3_bucket_arn = module.s3_raw_sop_bucket.bucket_arn
}

module "sqs_data_ingestion_queue" {
  source        = "./modules/sqs/data_ingestion_queue"
  prefix        = local.common_prefix
  environment   = local.common_prefix
  s3_bucket_arn = module.s3_standardized_bucket.bucket_arn
}

module "sqs_vector_queue" {
  source        = "./modules/sqs/vector_queue"
  prefix        = local.common_prefix
  environment   = local.common_prefix
  s3_bucket_arn = module.s3_standardized_bucket.bucket_arn
}

module "sqs_vector_nonprocess_queue" {
  source      = "./modules/sqs/vector_queue_nonprocess"
  prefix      = local.common_prefix
  environment = local.common_prefix
}

module "stepfunctions_pre_formatting_workflow" {
  source                               = "./modules/stepfunctions/pre_formatting_workflow"
  prefix                               = local.common_prefix
  environment                          = local.environment # Using local.environment
  detect_file_type_lambda_arn          = module.lambda_detect_file_type.lambda_function_arn
  pdf_extract_lambda_arn               = module.lambda_extract_content.pdf_lambda_function_arn
  office_extract_lambda_arn            = module.lambda_extract_content.office_lambda_function_arn
  duplicate_detection_lambda_arn       = module.lambda_check_duplicates.lambda_function_arn
  text_standardize_lambda_arn          = module.lambda_standardize_template.lambda_function_arn
  semantic_chunking_lambda_arn         = module.lambda_semantic_chunking.lambda_function_arn
  identify_distinct_process_lambda_arn = module.lambda_identify_distinct_process.lambda_function_arn
  create_process_docs_lambda_arn       = module.lambda_create_process_docs.lambda_function_arn
}

module "stepfunctions_data_ingestion_workflow" {
  source                                  = "./modules/stepfunctions/data_ingestion_workflow"
  prefix                                  = local.common_prefix
  environment                             = local.environment # Using local.environment
  read_process_from_s3_lambda_arn         = module.lambda_read_from_process_s3.lambda_function_arn
  llm_based_tagging_lambda_arn            = module.lambda_llm_tagging.lambda_function_arn
  add_LLMTags_To_ProcessedDocs_lambda_arn = module.lambda_add_llm_tags_to_s3.lambda_function_arn
}

module "stepfunctions_vectorindex_workflow" {
  source                  = "./modules/stepfunctions/vectorindex_workflow"
  prefix                  = local.common_prefix
  environment             = local.environment # Using local.environment
  read_s3_lambda_arn      = module.read_sop_s3.lambda_function_arn
  chunk_lambda_arn        = module.chunk_sop.lambda_function_arn
  embed_lambda_arn        = module.generate_embedding.lambda_function_arn
  store_lambda_arn        = module.store_to_aoss.lambda_function_arn
  bedrock_sync_lambda_arn = module.bedrock_knowledge_base_process_docs.bedrock_sync_lambda_arn
}

module "stepfunctions_vectorindex_nonprocess_workflow" {
  source                        = "./modules/stepfunctions/vectorindex_nonprocess_workflow"
  prefix                        = local.common_prefix
  environment                   = local.environment
  read_s3_nonprocess_lambda_arn = module.read_sop_s3_nonprocess.lambda_function_arn
  chunk_nonprocess_lambda_arn   = module.chunk_sop_nonprocess.lambda_function_arn
  embed_nonprocess_lambda_arn   = module.generate_embedding_nonprocess.lambda_function_arn
  store_nonprocess_lambda_arn   = module.store_to_aoss_nonprocess.lambda_function_arn
  bedrock_sync_lambda_arn       = module.bedrock_knowledge_base_non_process_docs.bedrock_sync_lambda_arn
}

module "opensearch_knn" {
  source                  = "./modules/opensearch"
  encryption_policy_name  = "${local.common_prefix}-knn-enc-pol"
  network_policy_name     = "${local.common_prefix}-knn-net-pol"
  data_access_policy_name = "${local.common_prefix}-knn-data-pol"
  collection_name         = "${local.common_prefix}-collection"
  collection_type         = "VECTORSEARCH"
  principals = [
    "arn:aws:iam::381492081885:role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AdministratorAccess_04a46f8912deb967",
    module.store_to_aoss.lambda_role_arn,
    module.invoke_bedrock_llm.lambda_role_arn,
    module.review_handler.lambda_role_arn
  ]
  environment = local.environment
  index_name  = "${local.common_prefix}-index"
}

/*
module "bedrock_knowledge_base_process_docs" {
  source                              = "./modules/bedrock_kb_process_docs"
  prefix                              = local.common_prefix
  description                         = "Knowledge base for SOP ingestion process docs"
  existing_opensearch_collection_name = module.opensearch_knn.collection_name
  existing_opensearch_index_name      = module.opensearch_knn.index_name
  s3_bucket_arn                       = module.s3_standardized_bucket.bucket_arn
  environment                         = local.environment
  # This ensures the index is created before the Knowledge Base
  opensearch_index_creation_marker = module.opensearch_knn.index_creation_complete

  depends_on = [
    module.opensearch_knn
  ]
}
*/


module "opensearch_nonprocess_knn" {
  source = "./modules/opensearch_nonprocess"

  encryption_policy_name  = "${local.common_prefix}-knn-np-enc-pol"
  network_policy_name     = "${local.common_prefix}-knn-np-net-pol"
  data_access_policy_name = "${local.common_prefix}-knn-np-data-pol"
  collection_name         = "${local.common_prefix}-np-collection"
  collection_type         = "VECTORSEARCH"
  principals              = [
    "arn:aws:iam::381492081885:role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AdministratorAccess_04a46f8912deb967", 
    module.store_to_aoss_nonprocess.lambda_role_arn, 
    module.invoke_bedrock_llm.lambda_role_arn,
    module.review_handler.lambda_role_arn
  ]
  environment             = local.environment
  index_name              = "${local.common_prefix}-nonprocess-index"
}

/*
module "bedrock_knowledge_base_non_process_docs" {
  source                              = "./modules/bedrock_kb_non_process_docs"
  prefix                              = local.common_prefix
  description                         = "Knowledge base for SOP ingestion non process docs"
  existing_opensearch_collection_name = module.opensearch_knn.collection_name
  existing_opensearch_index_name      = module.opensearch_knn.index_name
  s3_bucket_arn                       = module.s3_text_extract_bucket.bucket_arn
  environment                         = local.environment
  opensearch_index_creation_marker    = module.opensearch_knn.index_creation_complete

  depends_on = [
    module.opensearch_nonprocess_knn
  ]
}
*/

module "ecr_pre_format_repo" {
  source                  = "./modules/lambda/backend/pre_formatting/ecr_repo"
  prefix                  = local.common_prefix
  repository_name         = "${local.common_prefix}-pre-format-repo"
  image_tag_mutability    = "MUTABLE"
  force_delete            = true
  scan_on_push            = true
  environment             = local.environment
  project_name            = "AI-KB"
  enable_lifecycle_policy = true
  lifecycle_count_number  = 30
}

module "ecr_data_ingestion_repo" {
  source                  = "./modules/lambda/backend/data_ingestion/ecr_repo"
  prefix                  = local.common_prefix
  repository_name         = "${local.common_prefix}-data-ingestion-repo"
  image_tag_mutability    = "MUTABLE"
  force_delete            = true
  scan_on_push            = true
  environment             = local.environment
  project_name            = "AI-KB"
  enable_lifecycle_policy = true
  lifecycle_count_number  = 30
}

module "ecr_vectorization_repo" {
  source                  = "./modules/lambda/backend/vectorization_and_storage/ecr_repo"
  prefix                  = local.common_prefix
  repository_name         = "${local.common_prefix}-vectorization-repo"
  image_tag_mutability    = "MUTABLE"
  force_delete            = true
  scan_on_push            = true
  environment             = local.environment
  project_name            = "AI-KB"
  enable_lifecycle_policy = true
  lifecycle_count_number  = 30
}

module "ecr_vectorization_np_repo" {
  source                  = "./modules/lambda/backend/vectorization_and_storage_nonprocess/ecr_repo"
  prefix                  = local.common_prefix
  repository_name         = "${local.common_prefix}-vectorization-np-repo"
  image_tag_mutability    = "MUTABLE"
  force_delete            = true
  scan_on_push            = true
  environment             = local.environment
  project_name            = "AI-KB"
  enable_lifecycle_policy = true
  lifecycle_count_number  = 30
}
# RDS policy which can be used my and lambda module
resource "aws_iam_policy" "rds_data_api_policy" {
  name        = "${local.common_prefix}-lambda-rds-data-api"
  description = "Allows Lambda to execute SQL on Aurora via Data API"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "rds-data:ExecuteStatement",
          "rds-data:BatchExecuteStatement",
          "rds-data:BeginTransaction",
          "rds-data:CommitTransaction",
          "rds-data:RollbackTransaction"
        ],
        Resource = module.rds_postgres.cluster_arn
      }
    ]
  })
}

# --- Policy to allow reading from Secrets Manager ---
resource "aws_iam_policy" "secrets_manager_read_policy" {
  name        = "${local.common_prefix}-lambda-secrets-manager-read"
  description = "Allows Lambda to read the DB password secret from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret", # DescribeSecret is useful for more context
        ],
        Resource: [
        module.rds_postgres.master_secret_arn,
        "${module.rds_postgres.master_secret_arn}*"
      ]
      },
    ],
  })
}

module "lambda_detect_file_type" {
  source              = "./modules/lambda/backend/pre_formatting/detect_file_type"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_pre_format_repo.repository_name
  ecr_repository_url  = module.ecr_pre_format_repo.repository_url
  s3_bucket_id        = module.s3_raw_sop_bucket.bucket_name
  s3_bucket_arn       = module.s3_raw_sop_bucket.bucket_arn
  environment_variables = {
    LOG_LEVEL = "INFO"
  }
  environment = local.environment # Using local.environment
}

module "lambda_extract_content" {
  source = "./modules/lambda/backend/pre_formatting/text_extraction"
  prefix = local.common_prefix
  environment_vars = {
    LOG_LEVEL             = "INFO",
    EXTRACTED_TEXT_BUCKET = module.s3_text_extract_bucket.bucket_name
    REGION                = "ca-central-1"
  }
  environment = local.environment # Using local.environment
  aws_region  = "ca-central-1"
  REGION      = "ca-central-1"
}

module "lambda_check_duplicates" {
  source              = "./modules/lambda/backend/pre_formatting/check_for_duplicates"
  prefix              = local.common_prefix
  secrets_manager_read_policy_arn = aws_iam_policy.secrets_manager_read_policy.arn
  rds_data_api_policy_arn = aws_iam_policy.rds_data_api_policy.arn
  rds_secret_arn      = module.rds_postgres.master_secret_arn
  rds_cluster_arn     = module.rds_postgres.cluster_arn
  ecr_repository_name = module.ecr_pre_format_repo.repository_name
  ecr_repository_url  = module.ecr_pre_format_repo.repository_url
  environment_vars = {
    LOG_LEVEL      = "INFO"
    PGHOST         = module.rds_postgres.writer_endpoint
    PGPORT         = tostring(module.rds_postgres.port)
    PGDATABASE     = module.rds_postgres.db_name
    DB_SECRET_NAME = module.rds_postgres.master_secret_arn
    DB_CLUSTER_ARN = module.rds_postgres.cluster_arn
  }
  environment = local.environment
}

module "lambda_standardize_template" {
  source              = "./modules/lambda/backend/pre_formatting/text_standardize"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_pre_format_repo.repository_name
  ecr_repository_url  = module.ecr_pre_format_repo.repository_url
  environment_vars = {
    LOG_LEVEL       = "INFO",
    TEXT_STD_BUCKET = module.s3_text_extract_bucket.bucket_name
  }
  environment = local.environment # Using local.environment
}

module "lambda_create_process_docs" {
  source              = "./modules/lambda/backend/pre_formatting/create_process_docs"
  prefix              = local.common_prefix
  output_bucket       = module.s3_standardized_bucket.bucket_arn
  ecr_repository_name = module.ecr_pre_format_repo.repository_name
  ecr_repository_url  = module.ecr_pre_format_repo.repository_url
  secrets_manager_read_policy_arn = aws_iam_policy.secrets_manager_read_policy.arn
  rds_data_api_policy_arn = aws_iam_policy.rds_data_api_policy.arn
  rds_secret_arn = module.rds_postgres.master_secret_arn
  rds_cluster_arn = module.rds_postgres.cluster_arn
  environment_vars = {
    LOG_LEVEL     = "INFO"
    OUTPUT_BUCKET = module.s3_standardized_bucket.bucket_name
    PGHOST         = module.rds_postgres.writer_endpoint
    PGPORT         = tostring(module.rds_postgres.port)
    PGDATABASE     = module.rds_postgres.db_name
    DB_SECRET_NAME = module.rds_postgres.master_secret_arn
    DB_CLUSTER_ARN = module.rds_postgres.cluster_arn
  }
  environment = local.environment # Using local.environment
}

module "lambda_identify_distinct_process" {
  source              = "./modules/lambda/backend/pre_formatting/identify_distinct_process"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_pre_format_repo.repository_name
  ecr_repository_url  = module.ecr_pre_format_repo.repository_url
  environment_vars = {
    LOG_LEVEL               = "INFO"
    DISTINCT_PROCESS_BUCKET = module.s3_text_extract_bucket.bucket_name
  }
  environment = local.environment # Using local.environment
}

module "lambda_semantic_chunking" {
  source              = "./modules/lambda/backend/pre_formatting/semantic_chunking"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_pre_format_repo.repository_name
  ecr_repository_url  = module.ecr_pre_format_repo.repository_url
  environment_vars = {
    LOG_LEVEL                = "INFO"
    USE_CLAUDE               = "true"
    BEDROCK_REGION           = "ca-central-1"
    MODEL_ID                 = "anthropic.claude-3-sonnet-20240229-v1:0"
    SEMANTIC_CHUNKING_BUCKET = module.s3_text_extract_bucket.bucket_name
  }
  environment = local.environment # Using local.environment
}

module "lambda_read_from_process_s3" {
  source = "./modules/lambda/backend/data_ingestion/read_from_process_s3"
  prefix = local.common_prefix
  environment_variables = {
    LOG_LEVEL = "INFO"
  }
  environment         = local.environment
  ecr_repository_name = module.ecr_data_ingestion_repo.repository_name
  ecr_repository_url  = module.ecr_data_ingestion_repo.repository_url
}

module "lambda_llm_tagging" {
  source = "./modules/lambda/backend/data_ingestion/llm_tagging"
  prefix = local.common_prefix
  environment_variables = {
    LOG_LEVEL = "INFO"
  }
  environment         = local.environment
  ecr_repository_name = module.ecr_data_ingestion_repo.repository_name
  ecr_repository_url  = module.ecr_data_ingestion_repo.repository_url
}

module "lambda_add_llm_tags_to_s3" {
  source              = "./modules/lambda/backend/data_ingestion/add_llm_tags_to_s3"
  prefix              = local.common_prefix
  environment         = local.environment
  s3_bucket_name      = module.s3_standardized_bucket.bucket_name
  secrets_manager_read_policy_arn = aws_iam_policy.secrets_manager_read_policy.arn
  rds_data_api_policy_arn = aws_iam_policy.rds_data_api_policy.arn
  rds_secret_arn      = module.rds_postgres.master_secret_arn
  rds_cluster_arn     = module.rds_postgres.cluster_arn
  ecr_repository_name = module.ecr_data_ingestion_repo.repository_name
  ecr_repository_url  = module.ecr_data_ingestion_repo.repository_url
  environment_variables = {
    LOG_LEVEL      = "INFO"
    PGHOST         = module.rds_postgres.writer_endpoint
    PGPORT         = tostring(module.rds_postgres.port)
    PGDATABASE     = module.rds_postgres.db_name
    DB_SECRET_NAME = module.rds_postgres.master_secret_arn
    DB_CLUSTER_ARN = module.rds_postgres.cluster_arn
  }
}

# --- END UPDATED Lambda module calls ---

module "read_sop_s3" {
  source              = "./modules/lambda/backend/vectorization_and_storage/read_sop_s3"
  prefix              = local.common_prefix
  bucket_name         = module.s3_standardized_bucket.bucket_name
  ecr_repository_name = module.ecr_vectorization_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_repo.repository_url
  environment_variables = {
    LOG_LEVEL = "INFO"
    S3_BUCKET = module.s3_standardized_bucket.bucket_arn
  }
  environment = local.environment
}

module "chunk_sop" {
  source              = "./modules/lambda/backend/vectorization_and_storage/chunk_sop"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_vectorization_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_repo.repository_url
  environment_variables = {
    LOG_LEVEL               = "INFO"
    CHUNK_SIZE              = 500
    CHUNK_OVERLAP           = 50
    INCLUDE_IMAGE_REFS      = true
    SEPARATE_IMAGE_CHUNKS   = false
    INCLUDE_TAGGING_INFO    = true
    SEPARATE_TAGGING_CHUNKS = true
  }
  environment = local.environment
}

module "generate_embedding" {
  source              = "./modules/lambda/backend/vectorization_and_storage/generate_embedding"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_vectorization_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_repo.repository_url
  environment_variables = {
    LOG_LEVEL        = "INFO"
    BEDROCK_MODEL_ID = "amazon.titan-embed-text-v2:0"
    OUTPUT_BUCKET    = module.s3_embedding_bucket.bucket_name
  }
  environment = local.environment
}

module "store_to_aoss" {
  source              = "./modules/lambda/backend/vectorization_and_storage/store_to_aoss"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_vectorization_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_repo.repository_url
  environment_variables = {
    LOG_LEVEL     = "INFO"
    AOSS_ENDPOINT = module.opensearch_knn.collection_endpoint
    AOSS_INDEX    = "${local.common_prefix}-index"
  }
  environment = local.environment
}

# --- Non-process docs vectorization flow ---
module "read_sop_s3_nonprocess" {
  source              = "./modules/lambda/backend/vectorization_and_storage_nonprocess/read_sop_s3"
  prefix              = local.common_prefix
  bucket_name         = module.s3_text_extract_bucket.bucket_name
  ecr_repository_name = module.ecr_vectorization_np_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_np_repo.repository_url
  environment_variables = {
    LOG_LEVEL = "INFO"
    S3_BUCKET = module.s3_text_extract_bucket.bucket_arn
  }
  environment = local.environment
}

module "chunk_sop_nonprocess" {
  source              = "./modules/lambda/backend/vectorization_and_storage_nonprocess/chunk_sop"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_vectorization_np_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_np_repo.repository_url
  environment_variables = {
    LOG_LEVEL               = "INFO"
    CHUNK_SIZE              = 500
    CHUNK_OVERLAP           = 50
    INCLUDE_IMAGE_REFS      = true
    SEPARATE_IMAGE_CHUNKS   = false
    INCLUDE_TAGGING_INFO    = true
    SEPARATE_TAGGING_CHUNKS = true
  }
  environment = local.environment
}

module "generate_embedding_nonprocess" {
  source              = "./modules/lambda/backend/vectorization_and_storage_nonprocess/generate_embedding"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_vectorization_np_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_np_repo.repository_url
  environment_variables = {
    LOG_LEVEL        = "INFO"
    BEDROCK_MODEL_ID = "amazon.titan-embed-text-v2:0"
    OUTPUT_BUCKET    = module.s3_embedding_nonprocess_bucket.bucket_name
  }
  environment = local.environment
}

module "store_to_aoss_nonprocess" {
  source              = "./modules/lambda/backend/vectorization_and_storage_nonprocess/store_to_aoss"
  prefix              = local.common_prefix
  ecr_repository_name = module.ecr_vectorization_np_repo.repository_name
  ecr_repository_url  = module.ecr_vectorization_np_repo.repository_url
  environment_variables = {
    LOG_LEVEL     = "INFO"
    AOSS_ENDPOINT = module.opensearch_nonprocess_knn.collection_endpoint
    AOSS_INDEX    = "${local.common_prefix}-nonprocess-index"
  }
  environment = local.environment
}

module "pre_formatting_sqs_to_stepfunc" {
  source            = "./modules/lambda/backend/pre_formatting/sqs_to_step_function"
  prefix            = local.common_prefix
  step_function_arn = module.stepfunctions_pre_formatting_workflow.step_function_arn
  sqs_queue_arn     = module.sqs_pre_formatting_queue.sqs_arn
}

module "data_ingestion_sqs_to_stepfunc" {
  source            = "./modules/lambda/backend/data_ingestion/sqs_to_step_function"
  prefix            = local.common_prefix
  step_function_arn = module.stepfunctions_data_ingestion_workflow.step_function_arn
  sqs_queue_arn     = module.sqs_data_ingestion_queue.sqs_arn
}

module "vectorizing_sqs_to_stepfunc" {
  source            = "./modules/lambda/backend/vectorization_and_storage/sqs_to_step_function"
  prefix            = local.common_prefix
  step_function_arn = module.stepfunctions_vectorindex_workflow.step_function_arn
  sqs_queue_arn     = module.sqs_vector_queue.sqs_arn
}

module "vectorizing_nonprocess_sqs_to_stepfunc" {
  source            = "./modules/lambda/backend/vectorization_and_storage_nonprocess/sqs_to_step_function"
  prefix            = local.common_prefix
  step_function_arn = module.stepfunctions_vectorindex_nonprocess_workflow.step_function_arn
  sqs_queue_arn     = module.sqs_vector_nonprocess_queue.sqs_arn
}

/*
# --- Cloudfront configuration
# Chat UI CloudFront configuration
module "chat_ui_cdn" {
  source = "./modules/cloudfront"
  prefix = local.common_prefix
  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
  site_name           = "chat-ui"
  environment         = local.environment
  default_root_object = "index.html"
  comment             = "chat-ui static site (${local.environment})"
  price_class         = "PriceClass_100"
}



# Review UI CloudFront configuration
module "review_ui_cdn" {
  source = "./modules/cloudfront"
  prefix = local.common_prefix
  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
  site_name           = "review-ui"
  environment         = local.environment
  default_root_object = "index.html"
  comment             = "review-ui static site (${local.environment})"
  price_class         = "PriceClass_100"
}


# ---  RDS Deployment configuration --- -- commenting this section for now to check xlsx flow  -- 'mon' workspace


module "rds_postgres" {
  source      = "./modules/rds_postgres"
  name        = "${local.common_prefix}-postgres"
  environment = local.environment
  username    = "intouchx_admin"
  db_name     = "tsh-industries_db"
  vpc_id      = local.vpc_id
  subnet_ids  = local.private_subnets
  # Keep it private
  publicly_accessible            = false
  enable_cloudwatch_logs_exports = ["postgresql"]
  # Allow destroy without final snapshot
  skip_final_snapshot = true
  #added these for seamless destroy
  deletion_protection   = false # Prevents AWS from blocking deletion
  apply_immediately     = true  # Skips maintenance window delays
  backup_retention_days = 1     # Reduces backup cleanup time

  # Allow Lambda security groups to connect
  allowed_security_group_ids = [
    module.chat_handler.chat_security_group_id,
    module.review_handler.review_security_group_id
  ]
}

# --- Create IAM policy to allow reading Aurora DB secret ---
resource "aws_iam_policy" "read_db_secret" {
  name        = "${local.common_prefix}-read-db-secret"
  description = "Allow invoking Lambda to read Aurora DB master secret"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid : "ReadDbSecret",
      Effect : "Allow",
      Action : [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      Resource : [
        module.rds_postgres.master_secret_arn,
        "${module.rds_postgres.master_secret_arn}*"
      ]
    }]
  })

  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}


# --- Attach policy to the Lambda execution role ---
resource "aws_iam_role_policy_attachment" "chat_attach_read_db_secret" {
  role       = module.chat_handler.lambda_role_name
  policy_arn = aws_iam_policy.read_db_secret.arn
}

locals {
  vpce_https_ingress_sg_ids = distinct(compact([
    module.chat_handler.chat_security_group_id,
    module.review_handler.review_security_group_id
  ]))
}

# --- SG that allows Lambda SG to reach the endpoint on 443 ---
resource "aws_security_group" "vpce_https" {
  name        = "${local.common_prefix}-vpce-https"
  description = "HTTPS to VPC Interface Endpoints from Lambda"
  vpc_id      = local.vpc_id

  dynamic "ingress" {
    for_each = local.vpce_https_ingress_sg_ids
    content {
      description     = "Allow Lambda SG to access VPC endpoints on 443"
      from_port       = 443
      to_port         = 443
      protocol        = "tcp"
      security_groups = [ingress.value]
    }
  }


  egress {
    description = "Allow all egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}

resource "aws_iam_role_policy_attachment" "review_attach_read_db_secret" {
  role       = module.review_handler.lambda_role_name
  policy_arn = aws_iam_policy.read_db_secret.arn
}

# Interface Endpoint for Secrets Manager
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnets # or your private subnets used by Lambda
  security_group_ids  = [aws_security_group.vpce_https.id]
  private_dns_enabled = true

  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}

# S3 Gateway VPC endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = module.vpc.private_route_table_ids
  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}

# --- Chat Application log groups ---
# Interface Endpoint for CloudWatch Logs
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnets              # private subnets where your Lambda runs
  security_group_ids  = [aws_security_group.vpce_https.id] # must allow egress 443
  private_dns_enabled = true

  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}

# Application Log Group
resource "aws_cloudwatch_log_group" "chat_app_logs" {
  name              = "${terraform.workspace}/tsh-industries/chatUI/app"
  retention_in_days = 30
  tags = {
    Service = "chatUI"
    Type    = "application"
  }
}

# Audit Log Group
resource "aws_cloudwatch_log_group" "chat_audit_logs" {
  name              = "${terraform.workspace}/tsh-industries/chatUI/audit"
  retention_in_days = 90
  tags = {
    Service = "chatUI"
    Type    = "audit"
  }
}

# --- Chat Handler definition
module "chat_handler" {
  source = "./modules/lambda/ui/chatUI"

  prefix      = local.common_prefix
  environment = local.environment
  aws_region  = var.aws_region

  # VPC configuration (optional)
  vpc_id         = local.vpc_id
  vpc_subnet_ids = local.private_subnets

  function_name          = "chat-handler"
  docker_context_relpath = "ui"
  image_tag              = "latest"
  architectures          = ["arm64"]

  # Lambda configuration
  timeout     = 600
  memory_size = 512

  app_log_group   = aws_cloudwatch_log_group.chat_app_logs.name
  audit_log_group = aws_cloudwatch_log_group.chat_audit_logs.name

  s3_bucket_names = [
    module.s3_raw_sop_bucket.bucket_name,
    module.s3_text_extract_bucket.bucket_name,
    module.s3_standardized_bucket.bucket_name
  ]
  
  # Environment variables
  environment_variables = {
    APP_NAME                     = "chat"
    LOG_FORMAT                   = "json"
    REGION                       = var.aws_region
    LOG_LEVEL                    = "INFO"
    BEDROCK_REGION               = var.aws_region
    MODEL_ID                     = "anthropic.claude-3-sonnet-20240229-v1:0"
    DISTINCT_PROCESSES_KB_ID     = module.bedrock_knowledge_base_process_docs.knowledge_base_id
    NON_DISTINCT_PROCESSES_KB_ID = module.bedrock_knowledge_base_non_process_docs.knowledge_base_id
    PGHOST                       = module.rds_postgres.writer_endpoint
    PGPORT                       = tostring(module.rds_postgres.port)
    PGDATABASE                   = module.rds_postgres.db_name
    DB_SECRET_NAME               = module.rds_postgres.master_secret_name
    DATA_BUCKET                  = module.s3_standardized_bucket.bucket_name
    APP_LOG_GROUP                = aws_cloudwatch_log_group.chat_app_logs.name
    AUDIT_LOG_GROUP              = aws_cloudwatch_log_group.chat_audit_logs.name
    ENABLE_MULTI_AGENT           = true
    AGENT_WORKFLOW_TIMEOUT       = 300
    AGENT_MAX_RETRIES            =  3
  }
}

# --- SG that allows 443 into the VPC endpoints from Lambda SGs (chat)
resource "aws_security_group" "vpce_https_bedrock" {
  name        = "${local.common_prefix}-vpce-bedrock-https"
  description = "HTTPS from Lambda SGs to Bedrock VPC endpoints"
  vpc_id      = local.vpc_id

  ingress {
    description     = "HTTPS from chat handler SG"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [module.chat_handler.chat_security_group_id]
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}

# ---  Bedrock runtime endpoint (data-plane)
resource "aws_vpc_endpoint" "bedrock_runtime" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnets
  security_group_ids  = [aws_security_group.vpce_https_bedrock.id]
  private_dns_enabled = true
  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}

# --- Bedrock agent runtime endpoint (for knowledge base operations)
resource "aws_vpc_endpoint" "bedrock_agent_runtime" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-agent-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnets
  security_group_ids  = [aws_security_group.vpce_https_bedrock.id]
  private_dns_enabled = true
  tags = {
    Environment = local.environment
    Name        = "AI-KB"
  }
}


# --- Review Handler Lambda:  module configuration ---
# Application Log Group
resource "aws_cloudwatch_log_group" "review_app_logs" {
  name              = "${terraform.workspace}/tsh-industries/reviewUI/app"
  retention_in_days = 30
  tags = {
    Service = "reviewUI"
    Type    = "application"
  }
}

# Audit Log Group
resource "aws_cloudwatch_log_group" "review_audit_logs" {
  name              = "${terraform.workspace}/tsh-industries/reviewUI/audit"
  retention_in_days = 90
  tags = {
    Service = "reviewUI"
    Type    = "audit"
  }
}

module "review_handler" {
  source      = "./modules/lambda/ui/reviewUI"
  prefix      = local.common_prefix
  environment = local.environment

  aws_region = var.aws_region

  app_log_group   = aws_cloudwatch_log_group.review_app_logs.name
  audit_log_group = aws_cloudwatch_log_group.review_audit_logs.name

  function_name          = "review-handler"
  docker_context_relpath = "ui"
  image_tag              = "latest"
  architectures          = ["arm64"]

  vpc_id         = local.vpc_id
  vpc_subnet_ids = local.private_subnets

  secrets_manager_read_policy_arn = aws_iam_policy.secrets_manager_read_policy.arn
  rds_data_api_policy_arn = aws_iam_policy.rds_data_api_policy.arn
  rds_secret_arn = module.rds_postgres.master_secret_arn
  rds_cluster_arn = module.rds_postgres.cluster_arn
  s3_bucket_names = [
    module.s3_raw_sop_bucket.bucket_name,
    module.s3_text_extract_bucket.bucket_name,
    module.s3_standardized_bucket.bucket_name
  ]

  environment_variables = {
    APP_NAME        = "review"
    LOG_LEVEL       = "INFO"
    LOG_FORMAT      = "json"
    REGION          = "ca-central-1"
    PGHOST          = module.rds_postgres.writer_endpoint # <-- writer (read/write)
    PGPORT          = tostring(module.rds_postgres.port)
    PGDATABASE      = module.rds_postgres.db_name
    DB_SECRET_NAME  = module.rds_postgres.master_secret_name
    DB_CLUSTER_ARN = module.rds_postgres.cluster_arn
    DATA_BUCKET     = module.s3_standardized_bucket.bucket_name
    APP_LOG_GROUP   = aws_cloudwatch_log_group.review_app_logs.name
    AUDIT_LOG_GROUP = aws_cloudwatch_log_group.review_audit_logs.name
    PROCESS_OPENSEARCH_ENDPOINT = module.opensearch_knn.collection_endpoint
    DOCUMENT_OPENSEARCH_ENDPOINT = module.opensearch_nonprocess_knn.collection_endpoint
    PROCESS_INDEX_NAME = module.opensearch_knn.index_name
    DOCUMENT_INDEX_NAME = module.opensearch_nonprocess_knn.index_name
  }
}

# --- IAM Policy for Review Handler Lambda to Access OpenSearch Serverless ---
resource "aws_iam_policy" "review_lambda_opensearch_access" {
  name        = "${local.common_prefix}-review-lambda-opensearch-access"
  description = "Allow review-handler Lambda to access OpenSearch Serverless collections"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          # OpenSearch Serverless API permissions
          "aoss:APIAccessAll"
        ],
        Resource = [
          module.opensearch_knn.collection_arn,
          module.opensearch_nonprocess_knn.collection_arn
        ]
      }
    ]
  })
}

# Attach to the review_handler Lambda role
resource "aws_iam_role_policy_attachment" "review_lambda_attach_opensearch_access" {
  role       = module.review_handler.lambda_role_name
  policy_arn = aws_iam_policy.review_lambda_opensearch_access.arn
}

module "api_gateway" {
  source      = "./modules/api_gateway"
  prefix      = local.common_prefix
  environment = local.environment

  chat_lambda_arn        = module.chat_handler.lambda_function_arn
  chat_lambda_invoke_arn = module.chat_handler.lambda_invoke_arn

  review_lambda_arn        = module.review_handler.lambda_function_arn
  review_lambda_invoke_arn = module.review_handler.lambda_invoke_arn


  # JWT config
  jwt_issuer    = var.jwt_issuer
  jwt_audiences = var.jwt_audiences
  allow_origins = var.allow_origins
  allow_methods = var.allow_methods
  allow_headers = var.allow_headers

  # Tighten CORS in prod - left as an example
  # allow_origins = ["https://your.domain"]
}
*/

module "invoke_bedrock_llm" {
  source                     = "./modules/lambda/backend/invoke_bedrock_llm"
  prefix                     = local.common_prefix
  opensearch_collection_name = "${local.common_prefix}-collection"
  environment_variables = {
    OPENSEARCH_ENDPOINT = module.opensearch_knn.collection_endpoint
    INDEX_NAME          = "${local.common_prefix}-collection"
    EMBEDDING_MODEL_ID  = "amazon.titan-embed-text-v2:0"
    LLM_MODEL_ID        = "anthropic.claude-3-sonnet-20240229-v1:0"
  }
  environment = local.environment
}

