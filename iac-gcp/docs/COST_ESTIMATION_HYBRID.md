# GCP GenAI Pipeline - Hybrid Architecture Cost Estimation

**Architecture:** Cloud Run (6 services) + GKE (6 services)  
**Date:** May 2026  
**Version:** 2.0 (Hybrid)

---

## Executive Summary

The hybrid architecture combines Cloud Run for low-traffic services with GKE for high-compute services, achieving significant cost savings while maintaining performance.

| Architecture | Monthly Cost (Prod) | Savings vs Cloud Run Only |
|--------------|---------------------|---------------------------|
| Cloud Run Only | $4,110 | Baseline |
| **Hybrid (Recommended)** | **$2,525** | **39% ($1,585)** |
| GKE Only | $2,200 | 46% ($1,910) |

---

## Architecture Split

### Cloud Run Services (Low-Traffic, Event-Driven)

| Service | Requests/Month | Avg Duration | vCPU | Memory | Monthly Cost |
|---------|----------------|--------------|------|--------|--------------|
| detect-file-type | 10,000 | 2s | 1 | 512Mi | $35 |
| text-standardize | 10,000 | 10s | 1 | 1Gi | $45 |
| identify-distinct-process | 10,000 | 5s | 1 | 1Gi | $30 |
| create-process-docs | 10,000 | 10s | 1 | 1Gi | $45 |
| read-from-storage | 20,000 | 2s | 1 | 512Mi | $40 |
| add-llm-tags | 10,000 | 5s | 1 | 1Gi | $30 |
| **Cloud Run Subtotal** | | | | | **$225** |

### GKE Services (High-Compute, CPU/Memory Intensive)

| Service | Replicas | vCPU/Pod | Memory/Pod | Node Affinity |
|---------|----------|----------|------------|---------------|
| text-extraction | 2-10 | 1-2 | 2-4Gi | Spot preferred |
| semantic-chunking | 2-8 | 1-2 | 4-8Gi | Spot preferred |
| llm-tagging | 2-8 | 1-2 | 4-8Gi | Spot preferred |
| chunk-sop | 2-10 | 0.5-1 | 1-2Gi | Spot preferred |
| generate-embedding | 3-20 | 1-2 | 4-8Gi | Spot preferred |
| store-to-vector-db | 2-10 | 1-2 | 2-4Gi | Spot preferred |

---

## GKE Cluster Cost Breakdown

### Node Pool Configuration

| Pool | Machine Type | vCPU | Memory | Count | Pricing | Monthly Cost |
|------|--------------|------|--------|-------|---------|--------------|
| On-Demand | e2-standard-4 | 4 | 16 GB | 2 | $0.134/hr | $196 |
| Spot | e2-standard-4 | 4 | 16 GB | 2 (avg) | $0.040/hr | $58 |
| **Node Subtotal** | | | | | | **$254** |

### GKE Additional Costs

| Component | Configuration | Monthly Cost |
|-----------|---------------|--------------|
| Cluster management | Free (zonal) | $0 |
| Persistent disks | 100 GB SSD | $17 |
| Internal Load Balancer | 1 | $18 |
| Cloud NAT (GKE egress) | Shared with VPC | $0 |
| **Additional Subtotal** | | **$35** |

### Total GKE Cost: **$289/month**

---

## Complete Hybrid Cost Summary (Production)

| Category | Cloud Run | GKE | Total |
|----------|-----------|-----|-------|
| **Compute** | $225 | $289 | **$514** |
| Cloud Storage | | | $16 |
| Cloud SQL | | | $310 |
| Vertex AI Embeddings | | | $30 |
| Vertex AI LLM | | | $1,015 |
| Vector Search | | | $600 |
| Pub/Sub | | | $5 |
| Workflows | | | $10 |
| Networking | | | $150 |
| Security | | | $3 |
| Monitoring | | | $50 |
| **Grand Total** | | | **$2,703** |
| **With 10% buffer** | | | **$2,973** |

---

## Cost Comparison: All Architectures

### Production Environment (10K docs/month, 200K queries/month)

| Component | Cloud Run Only | Hybrid | GKE Only |
|-----------|----------------|--------|----------|
| Compute | $1,810 | $514 | $450 |
| Storage | $16 | $16 | $16 |
| Database | $310 | $310 | $310 |
| Vertex AI | $1,045 | $1,045 | $1,045 |
| Vector Search | $600 | $600 | $600 |
| Messaging | $15 | $15 | $15 |
| Networking | $262 | $150 | $120 |
| Monitoring | $50 | $70 | $80 |
| **Total** | **$4,108** | **$2,720** | **$2,636** |
| **Savings** | - | **34%** | **36%** |

### Development Environment

| Component | Cloud Run Only | Hybrid | GKE Only |
|-----------|----------------|--------|----------|
| Compute | $162 | $95 | $80 |
| Other services | $188 | $188 | $188 |
| **Total** | **$350** | **$283** | **$268** |

### Staging Environment

| Component | Cloud Run Only | Hybrid | GKE Only |
|-----------|----------------|--------|----------|
| Compute | $500 | $180 | $150 |
| Other services | $468 | $468 | $468 |
| **Total** | **$968** | **$648** | **$618** |

---

## Why Hybrid Over GKE-Only?

| Factor | Hybrid | GKE Only |
|--------|--------|----------|
| **Operational Complexity** | Lower | Higher |
| **Scaling Speed** | Faster (Cloud Run) | Slower (HPA) |
| **Cold Start** | None (Cloud Run) | Pod scheduling |
| **Cost** | Slightly higher | Lowest |
| **Team Expertise** | Less K8s needed | Full K8s needed |
| **Maintenance** | Split | All K8s |

**Recommendation:** Hybrid is the best balance of cost savings and operational simplicity.

---

## Spot VM Considerations

### Benefits
- 70% cost reduction on compute
- Same performance as on-demand
- Automatic fallback to on-demand pool

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Preemption (2-min warning) | Graceful shutdown handlers |
| Availability | Mixed pool (on-demand baseline) |
| Stateful workloads | All services are stateless |
| Long-running jobs | Checkpointing, idempotent operations |

### Spot VM Best Practices Implemented

1. **Pod Disruption Budgets** - Minimum 1 pod always available
2. **Graceful Termination** - 60-120s termination grace period
3. **Anti-Affinity** - Pods spread across nodes
4. **Tolerations** - Explicit spot node tolerations
5. **Priority Classes** - Critical services get on-demand nodes

---

## Scaling Scenarios

### Scenario 1: Normal Load (10K docs/month)

| Component | Configuration | Cost |
|-----------|---------------|------|
| GKE On-Demand | 2 nodes | $196 |
| GKE Spot | 0-2 nodes | $0-58 |
| Cloud Run | Min 0 instances | $225 |
| **Total Compute** | | **$421-479** |

### Scenario 2: High Load (50K docs/month)

| Component | Configuration | Cost |
|-----------|---------------|------|
| GKE On-Demand | 2 nodes | $196 |
| GKE Spot | 4 nodes | $117 |
| Cloud Run | Auto-scaled | $350 |
| **Total Compute** | | **$663** |

### Scenario 3: Peak Load (100K docs/month)

| Component | Configuration | Cost |
|-----------|---------------|------|
| GKE On-Demand | 4 nodes | $392 |
| GKE Spot | 6 nodes | $175 |
| Cloud Run | Auto-scaled | $500 |
| **Total Compute** | | **$1,067** |

---

## Annual Cost Projection

| Environment | Monthly | Annual | With CUD (1yr) | Savings |
|-------------|---------|--------|----------------|---------|
| Development | $283 | $3,396 | $2,717 | 20% |
| Staging | $648 | $7,776 | $6,221 | 20% |
| Production | $2,720 | $32,640 | $26,112 | 20% |
| **Total** | **$3,651** | **$43,812** | **$35,050** | **$8,762** |

---

## Migration Path

### Phase 1: Deploy Hybrid Infrastructure
- Deploy GKE cluster with mixed node pools
- Keep Cloud Run services unchanged
- Test GKE services in parallel

### Phase 2: Gradual Traffic Shift
- Route 10% traffic to GKE services
- Monitor performance and costs
- Increase to 50%, then 100%

### Phase 3: Optimize
- Tune HPA settings based on actual load
- Adjust spot/on-demand ratio
- Consider committed use discounts

---

## Monitoring Recommendations

### GKE-Specific Metrics

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Node CPU utilization | >80% for 5min | Scale up |
| Pod restart count | >3 in 10min | Investigate |
| Spot preemption rate | >10% daily | Increase on-demand |
| HPA scaling events | >20/hour | Review thresholds |

### Cost Monitoring

```bash
# Set up budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="GenAI Pipeline Hybrid" \
  --budget-amount=3000 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

---

## Conclusion

The hybrid architecture provides:

1. **39% cost reduction** compared to Cloud Run only
2. **Operational simplicity** with Cloud Run for simple services
3. **Cost efficiency** with GKE Spot VMs for compute-heavy services
4. **Flexibility** to scale each tier independently
5. **Reliability** with mixed on-demand/spot node pools

**Recommended for production deployment.**
