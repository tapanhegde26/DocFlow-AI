# modules/cloud_workflows/pre_formatting_workflow_hybrid/main.tf
# Hybrid workflow: Cloud Run + GKE services

resource "google_workflows_workflow" "pre_formatting_hybrid" {
  name            = "${var.prefix}-pre-formatting-workflow-hybrid"
  project         = var.project_id
  region          = var.region
  description     = "Pre-formatting workflow (hybrid: Cloud Run + GKE)"
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

    # Step 1: Detect file type (Cloud Run - low compute)
    - detect_file_type:
        call: http.post
        args:
          url: ${var.detect_file_type_url}
          auth:
            type: OIDC
          body:
            bucket: $${bucket}
            object_name: $${object_name}
          timeout: 300
        result: file_type_result

    - check_file_type:
        switch:
          - condition: $${file_type_result.body.file_type == "pdf"}
            next: extract_pdf
          - condition: $${file_type_result.body.file_type == "office"}
            next: extract_office
        next: end_unsupported

    # Step 2: Text extraction (GKE - high compute)
    - extract_pdf:
        call: http.post
        args:
          url: ${var.text_extraction_url}/extract
          body:
            bucket: $${bucket}
            object_name: $${object_name}
            file_type: "pdf"
          timeout: 600
        result: extraction_result
        next: standardize_text

    - extract_office:
        call: http.post
        args:
          url: ${var.text_extraction_url}/extract
          body:
            bucket: $${bucket}
            object_name: $${object_name}
            file_type: "office"
          timeout: 600
        result: extraction_result
        next: standardize_text

    # Step 3: Text standardization (Cloud Run - low compute)
    - standardize_text:
        call: http.post
        args:
          url: ${var.text_standardize_url}
          auth:
            type: OIDC
          body:
            bucket: $${extraction_result.body.output_bucket}
            object_name: $${extraction_result.body.output_key}
          timeout: 300
        result: standardize_result

    # Step 4: Semantic chunking (GKE - high compute, LLM calls)
    - semantic_chunking:
        call: http.post
        args:
          url: ${var.semantic_chunking_url}/chunk
          body:
            bucket: $${standardize_result.body.output_bucket}
            object_name: $${standardize_result.body.output_key}
          timeout: 600
        result: chunking_result

    # Step 5: Identify distinct process (Cloud Run - low compute)
    - identify_distinct_process:
        call: http.post
        args:
          url: ${var.identify_distinct_process_url}
          auth:
            type: OIDC
          body:
            bucket: $${chunking_result.body.output_bucket}
            object_name: $${chunking_result.body.output_key}
          timeout: 300
        result: identify_result

    # Step 6: Create process docs (Cloud Run - low compute)
    - create_process_docs:
        call: http.post
        args:
          url: ${var.create_process_docs_url}
          auth:
            type: OIDC
          body:
            bucket: $${identify_result.body.output_bucket}
            distinct_processes: $${identify_result.body.distinct_processes}
            non_distinct_processes: $${identify_result.body.non_distinct_processes}
          timeout: 300
        result: create_docs_result

    - return_success:
        return:
          status: "success"
          message: "Pre-formatting workflow completed (hybrid)"
          output: $${create_docs_result.body}

    - end_unsupported:
        return:
          status: "skipped"
          message: "Unsupported file type"
EOF

  labels = var.labels
}
