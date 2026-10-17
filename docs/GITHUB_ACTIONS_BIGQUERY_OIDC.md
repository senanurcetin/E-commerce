# NEXUS Commerce Intelligence — BigQuery via GitHub Actions OIDC

## Purpose and scope

GitHub repository: senanurcetin/nexus-commerce-intelligence (immutable repository ID 1217831974).
The manual workflow .github/workflows/bigquery-connection.yml authenticates
via google-github-actions/auth@v3 Workload Identity Federation. No
service-account JSON key or long-lived credential belongs in GitHub.

Targets are source-pinned to workintech-working.e_ticaret and
workintech-working.fvt_gsheet, four tables each. A run reads only
dataset/table schema metadata and performs SELECT 1 AS nexus_auth_probe
as a dry-run. It fetches no records and certifies no merchant finance.

## Google Cloud Shell bootstrap

Use a project you ADMINISTER as IDENTITY_PROJECT. It may differ from
workintech-working, whose owner must separately authorize dataset metadata
access. BILLING_PROJECT must have a billing-enabled BigQuery API and grant
the service account permission to create BigQuery jobs.

~~~bash
export IDENTITY_PROJECT='YOUR_AUTHORIZED_IDENTITY_PROJECT'
export BILLING_PROJECT='YOUR_AUTHORIZED_BILLING_PROJECT'
export NUMBER="$(gcloud projects describe "$IDENTITY_PROJECT" --format='value(projectNumber)')"
export POOL='nexus-gha'
export PROVIDER='nexus-main'
export ACCOUNT='nexus-bq-readonly'
export SA="${ACCOUNT}@${IDENTITY_PROJECT}.iam.gserviceaccount.com"

gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com --project="$IDENTITY_PROJECT"
gcloud services enable bigquery.googleapis.com --project="$BILLING_PROJECT"
gcloud iam service-accounts create "$ACCOUNT" --project="$IDENTITY_PROJECT" --display-name='NEXUS GitHub BigQuery metadata'
gcloud iam workload-identity-pools create "$POOL" --project="$IDENTITY_PROJECT" --location=global --display-name='NEXUS GitHub'
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --project="$IDENTITY_PROJECT" --location=global --workload-identity-pool="$POOL" --issuer-uri='https://token.actions.githubusercontent.com/' --attribute-mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id' --attribute-condition="assertion.repository_id=='1217831974' && assertion.ref=='refs/heads/main' && assertion.event_name=='workflow_dispatch'"
gcloud iam service-accounts add-iam-policy-binding "$SA" --project="$IDENTITY_PROJECT" --role='roles/iam.workloadIdentityUser' --member="principalSet://iam.googleapis.com/projects/${NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository_id/1217831974"
gcloud projects add-iam-policy-binding "$BILLING_PROJECT" --role='roles/bigquery.jobUser' --member="serviceAccount:${SA}"
gcloud iam workload-identity-pools providers describe "$PROVIDER" --project="$IDENTITY_PROJECT" --location=global --workload-identity-pool="$POOL" --format='value(name)'
~~~

Grant the service account **BigQuery Metadata Viewer** on the two specific
datasets of workintech-working using BigQuery dataset Sharing → Permissions.
For actual future row SELECTs, an administrator may grant dataset-scoped
BigQuery Data Viewer, but it is not required for this metadata-only probe.
BigQuery Admin, Project Editor and long-lived JSON keys are unnecessary.

## GitHub Settings

Create Environment named bigquery-readonly in GitHub Settings → Environments.
Restrict branch to main and optionally require reviewer approval. Add
the following repository/environment Actions Variables, NOT credential JSON:

| Variable | Value |
| --- | --- |
| GCP_WIF_PROVIDER | Exact full provider name output above; includes numeric project number |
| GCP_BQ_SERVICE_ACCOUNT | Email of service account (SA) above |
| GCP_BQ_BILLING_PROJECT | Billing project ID above |

Run Actions → BigQuery OIDC metadata connection → Run workflow → main.
The only success claim is access to eight expected source-table schemas
and zero-row query job authorization. Do not upload source files, token
outputs or datasets as Actions artifacts.

## Existing NEXUS BigQuery preflights

scripts/ecommerce_bigquery_preflight.py and
integrations/greenweez/scripts/load_gsheet_from_bigquery.py now accept
the temporary GOOGLE_APPLICATION_CREDENTIALS file created by auth@v3,
with legacy local gcloud-user token fallback. Their full preflights
require separate preexisting local metadata inventory/mapping evidence
in gitignored target/cloud_inventory. The connection workflow does
not run them automatically and never adds the Greenweez --execute flag.

GitHub metadata and Workload Identity permissions may take several minutes
to propagate. 403 usually indicates the service account lacks metadata
rights in workintech-working or jobUser in BILLING_PROJECT, while an
invalid-identity error usually indicates pool/provider/role-binding mismatch.

References:
- https://github.com/google-github-actions/auth
- https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
- https://cloud.google.com/bigquery/docs/access-control
