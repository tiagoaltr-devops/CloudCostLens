# CloudCostLens

Lightweight OCI-focused cloud cost visibility platform.

## Architecture

- **Backend (FastAPI + APScheduler + Motor)**
  - OCI resource inventory collector (daily)
  - Pricing resolver with 7-day cache and fallback chain
  - Cost engine with resource cost-component decomposition
  - MongoDB summarized storage (`daily_cost_summary`)
  - REST API for dashboard and report export
- **Frontend (React + Vite + Recharts)**
  - KPI overview (daily/monthly/resource count)
  - Trend chart, service pie chart, compartment table
- **Deployment**
  - Dockerfiles for backend/frontend
  - `docker-compose` for local stack
  - Kubernetes manifests for OKE-style deployment

## Supported OCI resources (initial)

- Compute instances
- DB systems
- Autonomous databases
- Exadata infrastructure
- OKE clusters
- Boot volumes
- Block volumes
- Volume backups
- Load balancers
- Object storage buckets
- File storage systems

## Backend API

- `GET /costs/daily`
- `GET /costs/by-resource`
- `GET /costs/by-service`
- `GET /costs/by-compartment`
- `GET /costs/trend`
- `GET /resources`
- `GET /reports/export?format=csv|json|pdf&group_by=service|compartment|resource`
- `POST /collector/run`
- `GET /health`

Filters supported on cost endpoints:
- `start_date`, `end_date`
- `region`
- `compartment`
- `service_type`
- `tag` (format: `key:value`)

## Data model (summarized)

Collection: `daily_cost_summary`

```json
{
  "date": "2026-03-06",
  "tenancy": "ocid1.tenancy...",
  "region": "us-ashburn-1",
  "compartment": "prod",
  "resource_type": "compute_instance",
  "resource_id": "ocid1.instance...",
  "resource_name": "prod-app-server",
  "tags": {"env": "prod"},
  "cost_components": {
    "ocpu": 1.20,
    "memory": 0.35,
    "boot_volume": 0.15,
    "block_volume": 0.20
  },
  "total_daily_cost": 1.90
}
```

## Run locally

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- UI: `http://localhost:8080`

## Security

Use one of:
- OCI config mounted as file
- Kubernetes Secret
- Environment variables

Credentials are never hardcoded.

## Extensibility

Backend modules are split by `collectors`, `pricing`, `services`, and `models` to allow future provider adapters (AWS/Azure/GCP).
