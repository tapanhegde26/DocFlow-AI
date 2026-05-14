# modules/cloud_workflows/data_ingestion_workflow/main.tf

resource "google_workflows_workflow" "data_ingestion" {
  name            = "${var.prefix}-data-ingestion-workflow"
  project         = var.project_id
  region          = var.region
  description     = "Data ingestion workflow for LLM-based tagging"
  service_account = var.service_account

  source_contents = <<-EOF
main:
  params: [event]
  steps:
    - init:
        assign:
          - project_id: ${var.project_id}
          - bucket: $${event.data.bucket}
          - object_name: $${event.data.name}

    - read_from_storage:
        call: http.post
        args:
          url: ${var.read_from_storage_url}
          auth:
            type: OIDC
          body:
            bucket: $${bucket}
            object_name: $${object_name}
          timeout: 300
        result: read_result

    - llm_tagging:
        call: http.post
        args:
          url: ${var.llm_tagging_url}
          auth:
            type: OIDC
          body:
            content: $${read_result.body.content}
            metadata: $${read_result.body.metadata}
          timeout: 600
        result: tagging_result

    - add_llm_tags:
        call: http.post
        args:
          url: ${var.add_llm_tags_url}
          auth:
            type: OIDC
          body:
            bucket: $${bucket}
            object_name: $${object_name}
            content: $${read_result.body.content}
            tags: $${tagging_result.body.tags}
          timeout: 300
        result: add_tags_result

    - return_success:
        return:
          status: "success"
          message: "Data ingestion workflow completed"
          output: $${add_tags_result.body}
EOF

  labels = var.labels
}
