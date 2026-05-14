# modules/cloud_workflows/vectorindex_nonprocess_workflow/main.tf

resource "google_workflows_workflow" "vectorindex_nonprocess" {
  name            = "${var.prefix}-vectorindex-nonprocess-workflow"
  project         = var.project_id
  region          = var.region
  description     = "Vector indexing workflow for non-process documents"
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

    - read_sop:
        call: http.post
        args:
          url: ${var.read_sop_url}
          auth:
            type: OIDC
          body:
            bucket: $${bucket}
            object_name: $${object_name}
          timeout: 300
        result: read_result

    - chunk_sop:
        call: http.post
        args:
          url: ${var.chunk_sop_url}
          auth:
            type: OIDC
          body:
            content: $${read_result.body.content}
            metadata: $${read_result.body.metadata}
          timeout: 300
        result: chunk_result

    - generate_embeddings:
        call: http.post
        args:
          url: ${var.generate_embed_url}
          auth:
            type: OIDC
          body:
            chunks: $${chunk_result.body.chunks}
            metadata: $${read_result.body.metadata}
          timeout: 600
        result: embedding_result

    - store_to_vector_db:
        call: http.post
        args:
          url: ${var.store_vector_url}
          auth:
            type: OIDC
          body:
            embeddings: $${embedding_result.body.embeddings}
            metadata: $${read_result.body.metadata}
            index_type: "nonprocess"
          timeout: 600
        result: store_result

    - return_success:
        return:
          status: "success"
          message: "Non-process vector indexing workflow completed"
          vectors_stored: $${store_result.body.vectors_stored}
EOF

  labels = var.labels
}
