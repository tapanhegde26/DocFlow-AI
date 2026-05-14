# modules/cloud_workflows/vectorindex_workflow_hybrid/main.tf

resource "google_workflows_workflow" "vectorindex_hybrid" {
  name            = "${var.prefix}-vectorindex-workflow-hybrid"
  project         = var.project_id
  region          = var.region
  description     = "Vector indexing workflow (hybrid: Cloud Run + GKE)"
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

    # Step 1: Read SOP (Cloud Run - low compute)
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

    # Step 2: Chunk SOP (GKE - medium compute)
    - chunk_sop:
        call: http.post
        args:
          url: ${var.chunk_sop_url}/chunk
          body:
            content: $${read_result.body.content}
            metadata: $${read_result.body.metadata}
          timeout: 300
        result: chunk_result

    # Step 3: Generate embeddings (GKE - high compute, API calls)
    - generate_embeddings:
        call: http.post
        args:
          url: ${var.generate_embed_url}/embed
          body:
            chunks: $${chunk_result.body.chunks}
            metadata: $${read_result.body.metadata}
          timeout: 600
        result: embedding_result

    # Step 4: Store to vector DB (GKE - high compute, API calls)
    - store_to_vector_db:
        call: http.post
        args:
          url: ${var.store_vector_url}/store
          body:
            embeddings: $${embedding_result.body.embeddings}
            metadata: $${read_result.body.metadata}
            index_type: "process"
          timeout: 600
        result: store_result

    - return_success:
        return:
          status: "success"
          message: "Vector indexing workflow completed (hybrid)"
          vectors_stored: $${store_result.body.vectors_stored}
EOF

  labels = var.labels
}
