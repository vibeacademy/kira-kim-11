# Secrets and Environment Variables

Single source of truth for every secret and environment variable this
project reads, where each one is stored, and how to obtain it. Keep
this in sync when adding or removing env vars — the audit at the
bottom verifies completeness.

---

## How to read this document

Each row tells you:

| Column | Meaning |
|---|---|
| **Name** | Exact env var / secret / variable name. |
| **Used By** | Where it is read (file:line). Click through to confirm. |
| **Where Stored** | One of: `app .env` (local dev), `GitHub Actions secret`, `GitHub Actions variable`, `Cloud Run env var`, `Google Secret Manager`. |
| **How To Obtain** | The literal source of the value (Neon UI, GCP console, generated automatically, etc.). |
| **Required** | `Yes` / `No, has default`. |

If a value lives in more than one place (e.g. `DATABASE_URL` is set in
GitHub Actions per-PR and on the Cloud Run service), each location is
listed in **Where Stored**.

---

## Runtime app variables

Read by [app/config.py](../app/config.py). These are the only env
vars the running FastAPI app cares about. See [.env.example](../.env.example)
for the local-dev template.

| Name | Used By | Where Stored | How To Obtain | Required |
|---|---|---|---|---|
| `DATABASE_URL` | [app/config.py:18](../app/config.py#L18) | Local: `app .env`. Preview: GitHub Actions injects from Neon branch action output. Production: Cloud Run env var, sourced from `PRODUCTION_DATABASE_URL` GitHub Actions secret. | **Local SQLite**: leave default `sqlite:///./dev.db`. **Neon**: console.neon.tech → project → Branches → branch → Connect → toggle pooled connection ON → copy connection string. | No, has default for dev/test; required in `preview` and `production`. |
| `APP_URL` | [app/config.py:19](../app/config.py#L19) | Local: `app .env`. Cloud Run: env var on the service. | The public base URL the app is reachable at. Local default `http://localhost:8080`. Production: the Cloud Run service URL or a custom domain. | No, has default. |
| `ENVIRONMENT` | [app/config.py:20](../app/config.py#L20) | Local: `app .env`. Cloud Run: env var on the service (set per environment). | Choose one: `development`, `test`, `preview`, `production`. Drives the SQLite-vs-Postgres startup guard in `app/config.py`. | No, has default. |

---

## CI/CD secrets — Neon

Read by [.github/workflows/preview-deploy.yml](../.github/workflows/preview-deploy.yml)
and [.github/workflows/deploy.yml](../.github/workflows/deploy.yml).
Used to mint per-PR Neon branches and apply migrations.

| Name | Used By | Where Stored | How To Obtain | Required |
|---|---|---|---|---|
| `NEON_API_KEY` | preview-deploy.yml step `Create Neon branch`; preview-cleanup.yml step `Delete Neon branch` | GitHub Actions secret | console.neon.tech → top-right avatar → Account Settings → API Keys → New API Key. Save once — Neon never shows it again. | Yes (any preview deploy). |
| `NEON_PROJECT_ID` | preview-deploy.yml `Create Neon branch`; preview-cleanup.yml | GitHub Actions secret | console.neon.tech → project → Settings → General. Looks like `lingering-haze-12345678`. | Yes. |
| `NEON_PARENT_BRANCH` | preview-deploy.yml `Create Neon branch` (`parent` input) | GitHub Actions secret (only required if your Neon project's default branch is **not** named `main`) | console.neon.tech → project → Branches → look for the `default` badge → use that exact branch name. | Conditional. Set if the default branch is e.g. `production`. Otherwise the workflow falls back to `'main'`. |
| `PRODUCTION_DATABASE_URL` | [deploy.yml:93](../.github/workflows/deploy.yml#L93) — runs `alembic upgrade head` against prod and injects as `DATABASE_URL` on Cloud Run | GitHub Actions secret | Pooled connection string of the Neon project's default branch (the same place `NEON_PARENT_BRANCH` points at). Must include `-pooler` in the host. | Yes (production deploys). |

---

## CI/CD variables — Neon

| Name | Used By | Where Stored | How To Obtain | Required |
|---|---|---|---|---|
| `NEON_DB_USER` | preview-deploy.yml `Create Neon branch` `username` input | GitHub Actions **variable** (not secret) | The DB role name on your Neon branch. Default is `neondb_owner`; only override if you renamed it. | No, defaults to `neondb_owner`. |

---

## CI/CD secrets — GCP

Used by both deploy workflows to push images to Artifact Registry and
deploy Cloud Run revisions. Two auth paths are supported: Workload
Identity Federation (preferred, keyless) and a service account JSON key
(workshop fallback).

| Name | Used By | Where Stored | How To Obtain | Required |
|---|---|---|---|---|
| `GCP_PROJECT_ID` | preview-deploy.yml + deploy.yml `env` block | GitHub Actions secret | console.cloud.google.com → top bar → project selector → ID column. | Yes. |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | preview-deploy.yml + deploy.yml when WIF auth is configured | GitHub Actions secret | Created via `scripts/provision-gcp-project.sh` (or manually: IAM → Workload Identity Federation → pool → provider → full resource path). | Yes for WIF (preferred). |
| `GCP_SERVICE_ACCOUNT` | preview-deploy.yml + deploy.yml when WIF auth is configured | GitHub Actions secret | Email of the service account that the workflow impersonates via WIF. Looks like `agile-flow-ci@<project-id>.iam.gserviceaccount.com`. | Yes for WIF. |
| `GCP_SA_KEY` | preview-deploy.yml + deploy.yml fallback when WIF is not set | GitHub Actions secret | IAM → Service Accounts → key → JSON. Workshop shortcut only — long-lived JSON keys are an anti-pattern in production. | Required only if WIF isn't configured. |

---

## CI/CD variables — GCP

| Name | Used By | Where Stored | How To Obtain | Required |
|---|---|---|---|---|
| `ARTIFACT_REPO` | preview-deploy.yml + deploy.yml — Artifact Registry repository name | GitHub Actions **variable** | The repo name you created in Artifact Registry (e.g. `agile-flow`). | Yes. |
| `CLOUD_RUN_SERVICE` | deploy.yml — Cloud Run service name to deploy to | GitHub Actions **variable** | The Cloud Run service name (e.g. `agile-flow-app`). | Yes (production deploys). |
| `GCP_REGION` | preview-deploy.yml + deploy.yml — Cloud Run + Artifact Registry region | GitHub Actions **variable** | A Cloud Run region (e.g. `us-central1`). | Yes. |

---

## Automatic / built-in

| Name | Used By | Where Stored | How To Obtain | Required |
|---|---|---|---|---|
| `GITHUB_TOKEN` | Many workflow steps for `gh` API access. | GitHub Actions automatic | Issued by GitHub on every workflow run. Do NOT set this manually — see [docs/UPSTREAM-TEMPLATE-FEEDBACK.md](UPSTREAM-TEMPLATE-FEEDBACK.md) for the known limitations of this token (e.g. it cannot manage Actions secrets, project boards, or branch protection). | Always present. |

---

## Setting CI secrets in a Codespaces fork

The Codespaces-issued `GITHUB_TOKEN` cannot write Actions secrets, so
`gh secret set …` returns `403: Resource not accessible by integration`.
Two options:

1. **UI fallback (simplest):** repo Settings → Secrets and variables →
   Actions → New repository secret. Direct URL:
   `https://github.com/<owner>/<repo>/settings/secrets/actions`.
2. **CLI fallback:** in a terminal inside the Codespace,
   ```bash
   unset GITHUB_TOKEN
   gh auth login --hostname github.com --scopes "repo,workflow"
   # paste a personal access token with the right scopes
   gh secret set NEON_API_KEY --repo <owner>/<repo>
   ```
   The new auth lasts only for the current shell because the env var
   `GITHUB_TOKEN` is restored on the next terminal.

---

## Lifecycle of a secret (worked example)

How `PRODUCTION_DATABASE_URL` flows through the system, end to end:

1. **Created** by you in console.neon.tech → project → Branches →
   default branch → Connect → pooled connection string copied.
2. **Stored** as a GitHub Actions secret named `PRODUCTION_DATABASE_URL`
   in repo Settings → Secrets and variables → Actions.
3. **Read** by [.github/workflows/deploy.yml:93](../.github/workflows/deploy.yml#L93)
   as `secrets.PRODUCTION_DATABASE_URL`.
4. **Used twice** in that workflow:
   - Step `Apply migrations`: passed as `DATABASE_URL` env var to
     `alembic upgrade head` so production migrations run before the
     new revision takes traffic.
   - Step `Deploy to Cloud Run`: passed via `--set-env-vars` so the
     Cloud Run service reads it at request time as `DATABASE_URL`
     in [app/config.py:18](../app/config.py#L18).
5. **Rotated** by repeating step 1 with a new password (Neon's UI has
   a "Reset password" button) and re-pasting the new connection string
   into the same secret.

---

## Audit

To verify this document covers every secret and variable the workflows
reference, run:

```bash
grep -RhoE 'secrets\.[A-Z_]+|vars\.[A-Z_]+' .github/workflows/ | sort -u
```

Every name in that output should appear somewhere in this file. As of
the latest update, the audit yields:

```
secrets.GCP_PROJECT_ID
secrets.GCP_SA_KEY
secrets.GCP_SERVICE_ACCOUNT
secrets.GCP_WORKLOAD_IDENTITY_PROVIDER
secrets.GITHUB_TOKEN
secrets.NEON_API_KEY
secrets.NEON_PARENT_BRANCH
secrets.NEON_PROJECT_ID
secrets.PRODUCTION_DATABASE_URL
vars.ARTIFACT_REPO
vars.CLOUD_RUN_SERVICE
vars.GCP_REGION
vars.NEON_DB_USER
```

All 13 are documented above. When you add a new secret or variable
to a workflow, also add a row here in the appropriate section, then
re-run the audit.
