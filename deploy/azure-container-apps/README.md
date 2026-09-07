# Azure Container Apps

One Container App per environment (`stage`, `prod`), pulling from Azure Container Registry with a managed identity (AcrPull). CI authenticates with OIDC federated credentials; no long-lived secrets in GitHub.

## One-time setup (platform team)

```bash
RG=<resource-group> ; LOC=<region> ; ACR=<acrname> ; ENVNAME=<aca-environment> ; APP=<app-name>
az acr create -g $RG -n $ACR --sku Basic
az containerapp env create -g $RG -n $ENVNAME -l $LOC
az identity create -g $RG -n ${APP}-identity
az role assignment create --assignee "$(az identity show -g $RG -n ${APP}-identity --query principalId -o tsv)" \
  --role AcrPull --scope "$(az acr show -n $ACR --query id -o tsv)"
az containerapp create -g $RG -n $APP --environment $ENVNAME \
  --image mcr.microsoft.com/k8se/quickstart:latest --target-port 8000 --ingress external \
  --user-assigned "$(az identity show -g $RG -n ${APP}-identity --query id -o tsv)" \
  --registry-server $ACR.azurecr.io --registry-identity "$(az identity show -g $RG -n ${APP}-identity --query id -o tsv)" \
  --min-replicas 1 --max-replicas 3 --cpu 0.5 --memory 1Gi \
  --env-vars APP_ENV=stage WEB_CONCURRENCY=1 PORT=8000 \
  --secrets database-url=<postgres-url> secret-key=<random> \
  --env-vars DATABASE_URL=secretref:database-url SECRET_KEY=secretref:secret-key
```

Probes: liveness `GET /health`, readiness `GET /health/db` (configure via `az containerapp update --yaml` or the portal).

Federated credential for GitHub: create an Entra app registration, add a federated credential for `repo:<org>/<repo>:environment:<stage|prod>`, grant it `AcrPush` on the registry and `Contributor` on the Container App. Store `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ACR_NAME`, `ACA_RESOURCE_GROUP`, `ACA_APP_NAME` as GitHub **environment variables** (not secrets; none are sensitive).

## Deploy

Actions → **Deploy (Azure Container Apps)** → choose environment (and optionally an image tag). The workflow updates the revision and waits for `/health` to report the deploying commit's `release_sha`.

## Scheduled jobs

Create a Container Apps **Job** from the same image with `--command python -m app.cli.<job>` and a cron trigger. Never point a job at `scripts/` (guarded by `scripts/check_runtime_entrypoints.py`).

## Database

Azure Database for PostgreSQL Flexible Server; connection string as an ACA secret. Migrations run on container start.
