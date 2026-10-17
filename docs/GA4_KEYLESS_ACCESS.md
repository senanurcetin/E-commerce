# NEXUS Commerce Lab — keyless GA4 from Windows

## Existing access

Analytics Viewer on the NEXUS Commerce Lab property is separate from Google Cloud service account IAM.
The current gcloud principal lacks iam.serviceAccounts.getAccessToken on nexus-commerce-lab@workintech-working.iam.gserviceaccount.com.
The previously uploaded service-account private key is considered compromised and must be revoked.

## One-time narrowly scoped Cloud IAM grant

An authorized Google Cloud IAM administrator must grant Service Account Token Creator ON THIS SERVICE ACCOUNT ONLY to the existing active gcloud user:

~~~powershell
$project = 'workintech-working'
$sa = 'nexus-commerce-lab@workintech-working.iam.gserviceaccount.com'
$me = (gcloud auth list --filter='status:ACTIVE' --format='value(account)').Trim()
gcloud iam service-accounts add-iam-policy-binding $sa --project=$project --member="user:$me" --role='roles/iam.serviceAccountTokenCreator'
~~~

Review the role and account before executing. Do not grant this role project-wide. A PERMISSION_DENIED here requires the account/project IAM administrator. The IAM Credentials API and Analytics Admin/Data APIs must be enabled.

## Test and export without any JSON key

~~~powershell
cd C:\Users\MONSTER\E-commerce
$env:NEXUS_GA4_KEYLESS_IMPERSONATION='1'
python -m scripts.ga4_property_preflight --resolve
$env:GA4_LAB_PROPERTY_ID='YOUR_VERIFIED_NUMERIC_PROPERTY_ID'
python -m scripts.lab_ga4_events --start 2026-10-16 --end 2026-10-17
python -m scripts.build_powerbi
Remove-Item Env:NEXUS_GA4_KEYLESS_IMPERSONATION -ErrorAction SilentlyContinue
Remove-Item Env:GA4_LAB_PROPERTY_ID -ErrorAction SilentlyContinue
~~~

The code obtains the active gcloud user's token in memory, exchanges it using IAMCredentials generateAccessToken for an Analytics read-only service-account token with a 30-minute lifetime, then calls the exact GA4 Lab property and hostname. No tokens are printed or persisted. No ad/sales events are manufactured if the export fails.

Production acceptance requires an actual Data API response and validated local source snapshot. The PBIP is re-generated only after that validation.