# Connect an AI assistant to GA4 and Google Ads

This guide runs the two **official Google MCP servers** as local processes on your own computer. The AI client communicates with them over standard input/output (stdio). The default configuration is read-only; the servers use your own Google credentials. Nothing here installs a hosted proxy or shares a developer identity with other customers.

You will create a private profile, generate a client configuration and copy it into your AI client's MCP settings. These settings do not create a hosted service or modify existing GA4 landing-report scheduling. You need an AI client that supports **local stdio MCP servers**; cloud-only clients cannot run a process on your computer without additional infrastructure.

## 1. Before you begin

- Install Python **3.11 or newer**, Git and [Google Cloud CLI](https://cloud.google.com/sdk/docs/install). Verify with `python3 --version`, `git --version` and `gcloud --version`. The examples use macOS/Linux; on Windows replace the virtual-environment paths with your platform's equivalents.
- Have access to the exact GA4 property and Google Ads customer you want to use. A manager account ID is not necessarily the target customer ID.
- Use **your own** Google Cloud project(s) and Google identities. Enable the **Google Analytics Data API** and **Analytics Admin API** for Analytics, and **Google Ads API** for Ads. Enable APIs in the project associated with each profile.
- Google Ads project access level and permitted use determine whether you can query real accounts. Google says newly enabled projects have test access; apply for an appropriate production access level such as Explorer if needed. See [access levels](https://developers.google.com/google-ads/api/docs/api-policy/access-levels) and [Google Ads policy notes](GOOGLE_ADS_POLICY.md). Do not use another customer's Cloud project or a shared access token.
- If the GA4 and Ads identities differ, keep them in separate credential files. For GA4 use an identity with `analytics.readonly` and Viewer access to the intended property. For Ads, use a Google identity with only the required account access; the `adwords` OAuth scope is not read-only on its own. A dedicated read-only Ads user, where available, is an additional protection.

Google's official [Analytics MCP setup](https://github.com/googleanalytics/google-analytics-mcp#setup-instructions-) and [Ads MCP setup](https://github.com/googleads/google-ads-mcp#quickstart--setup) are the authoritative references for their own integrations. OAuth credentials and Google Cloud configuration are sensitive. Never paste access tokens, refresh tokens, client secrets or credential JSON into the assistant, a GitHub issue or a repository.

## 2. Install the verified versions

In a terminal, from the repository checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[google-mcp]'
```

The optional extra installs this project's launchers and the official `analytics-mcp==1.1.0` and `google-ads-mcp==0.0.6` packages. Their respective source and Apache-2.0 licenses remain Google's; the packages are dependencies, not copied into this repository. The launcher checks the exact upstream versions before starting. Review and test any future version change, including its tools and permissions, before upgrading. Dependencies of these packages are not all locked; exact transitive reproducibility is not claimed.

## 3. Create separate Google credential files

The launcher reads a credential file for each service and never changes a shared default credential symlink. A service-account key, authorized-user ADC, external-account or impersonated-service-account JSON may be accepted by Google libraries, subject to that identity's actual permissions. Avoid service-account keys when an approved shorter-lived alternative is available. For Ads account changes, Google's policies require the end user to sign in manually; this guide's default AI setup only exposes read tools.

One method for **user OAuth credentials** is to use a separate Google Cloud CLI configuration directory for each identity. The following illustrates Analytics and Ads login with your own Google OAuth desktop-client JSON; replace the paths with your own. Ask your Cloud administrator to create and approve the OAuth client if necessary. This writes new ADC files under the two private directories rather than changing the CLI's normal default configuration:

```sh
mkdir -p "$HOME/.config/flai-google/analytics" "$HOME/.config/flai-google/ads"
chmod 700 "$HOME/.config/flai-google" "$HOME/.config/flai-google/analytics" "$HOME/.config/flai-google/ads"
CLOUDSDK_CONFIG="$HOME/.config/flai-google/analytics" gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=/absolute/path/to/your-oauth-client.json
CLOUDSDK_CONFIG="$HOME/.config/flai-google/ads" gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=/absolute/path/to/your-oauth-client.json
chmod 600 "$HOME/.config/flai-google/analytics/application_default_credentials.json" "$HOME/.config/flai-google/ads/application_default_credentials.json"
```

Sign in with the intended Google identity in each browser flow. The two logins can use different approved OAuth clients if needed. `CLOUDSDK_CONFIG` is set only for each command above; these commands do not use a shared default ADC path. Do not publish the OAuth client file or resulting ADC files. For production use, apply your organization's credential storage and encryption requirements. On some systems, command output can show credential paths; treat them as private.

Google OAuth refresh tokens can expire or be revoked for multiple reasons. In particular, an external OAuth consent screen in Testing mode may cause a seven-day refresh-token expiry for non-basic scopes; see [Google OAuth documentation](https://developers.google.com/identity/protocols/oauth2). If an API reports `invalid_grant`, inspect the correct Google Cloud project, consent configuration and identity before reauthorizing. Do not automatically change the OAuth publishing status or claim a permanent fix.

## 4. Make your private connection profile

Copy the [example profile](../integrations/profile.example.json) **outside** the repository, for example into a private directory. Its values are examples, not live accounts:

```sh
mkdir -p "$HOME/.config/flai-google"
chmod 700 "$HOME/.config/flai-google"
cp integrations/profile.example.json "$HOME/.config/flai-google/profile.json"
chmod 600 "$HOME/.config/flai-google/profile.json"
```

Edit the file with your own **absolute** credential-file paths and Cloud project IDs. Replace both example paths and both project IDs; a placeholder will not connect. Use the same project only if it is actually the correct project for both identities. The optional `login_customer_id` is the 10-digit **manager** ID when access is through a Google Ads manager account; remove the field when not needed. Do not put an Ads customer ID there unless it is actually the login manager. The target account is selected separately when you ask your AI to run a report.

The launcher rejects missing, non-absolute, symlinked, non-regular or group/world-accessible profile and credential files on POSIX. Example paths must point to real credential files before generation succeeds. Keep the directory and files private, and do not commit them. For independent clients or accounts, create distinct profile files and point each AI connection at the intended one.

## 5. Generate the AI-client configuration

From the repository checkout, use the venv created in step 2. Replace the two paths with **absolute** paths; this example resolves them locally without exposing token values:

```sh
.venv/bin/python -m integrations.client_config \
  --profile "$HOME/.config/flai-google/profile.json" \
  --python "$(pwd)/.venv/bin/python"
```

The command checks both sections and prints JSON with two server entries, `flai-analytics-readonly` and `flai-ads-readonly`. It prints paths but not credential contents. Paths and project names can still be private: do not publish the resulting configuration. A missing executable, unreadable/unsafe profile or malformed credential file causes an error; the selected interpreter also checks upstream package versions when a server starts.

Copy the two entries into your AI client's MCP configuration using that client's instructions. Preserve any existing servers; do not overwrite unrelated settings. Client formats differ: some accept the complete `mcpServers` JSON object, while others require server entries or commands separately. Restart the client or open a new session if it does not discover the connections. To avoid accidental output, do not run a stdio server directly as an ordinary command unless using an MCP client.

## 6. Verify your connection

In the AI client, first ask it to list available **read-only** tools, then identify the accessible Analytics property and Ads customer by ID and name. Verify the actual ID, time zone and currency before asking for performance. If a requested account is absent, do not substitute another. A Google Ads manager ID should be used only as `login_customer_id`, not as proof of the underlying customer's identity.

Then use the [ready-to-copy analysis scenarios](../scenarios/README.md): GA4 landing-page analysis, Google Ads campaign status and 3-/7-day comparisons, and a combined source-by-source report. They are instructions for an AI client, not automatic scheduled jobs. See [data interpretation](DATA_INTERPRETATION.md) for attribution, metrics and time-zone cautions.

## Read-only boundaries and troubleshooting

- Analytics starts without `--allow-write`, with `ANALYTICS_MCP_ALLOW_WRITE=false` and no inherited OAuth HTTP server settings. Ads starts with an integrity-checked configuration that disables `assets` and `labels`. The launcher clears unrelated inherited environment variables, including the upstream Ads HTTP OAuth proxy configuration. It exposes **local stdio**, not a public HTTP endpoint.
- The launcher pins and checks its expected versions. If installation changes a server or introduces additional mutation tools, the pinned version or tool-list tests must be reviewed before it is upgraded. MCP configuration is not an authorization sandbox: a user, another process, or a differently configured client can still use any permissions held by their Google credential. Never reuse the credential in an untrusted client.
- `invalid_grant` usually requires examining and possibly reauthorizing the specific profile. Do not overwrite the other profile or the default credentials. `PERMISSION_DENIED` can mean wrong account, missing property/Ads access, wrong project or insufficient API access. If a manager is required, verify `login_customer_id` separately.
- Test access for Google Ads cannot query production accounts; request the appropriate level in your own project. Usage may be subject to quota, permitted-use conditions and RMF. See [Google Ads policy notes](GOOGLE_ADS_POLICY.md). A successful MCP connection is not proof of policy compliance.
- This project does not implement budget, bid, campaign or keyword edits. The upstream Ads server's asset and label writes are limited in scope; enabling them for an autonomous assistant is not equivalent to verified human consent. Do not make changes without the specific user's approval and required Google sign-in/review.

## Optional: create one Ads label with explicit confirmation

A separate terminal utility supports **creating one label**, not campaign, budget, bid, asset or keyword changes. It does not expose a write-capable server to your AI client. Review [Google Ads policies](GOOGLE_ADS_POLICY.md), ensure your own project and signed-in Google user are authorized, and use only where permitted. The utility requires an `authorized_user` Ads credential in your private profile. An interactive terminal and typed confirmation are safeguards, not proof of a human identity or policy compliance.

Create a private JSON plan outside the repository, replacing the fictional values with the intended customer and label. The customer ID is 10 digits without hyphens. `description` and `background_color` are optional.

```json
{
  "customer_id": "1234567890",
  "name": "Review needed",
  "description": "A label for items to review",
  "background_color": "#336699"
}
```

Save it as, for example, `$HOME/.config/flai-google/label-plan.json` and restrict access (`chmod 600` on POSIX). From the project directory run:

```sh
.venv/bin/python -m manual_changes \
  --profile "$HOME/.config/flai-google/profile.json" \
  --plan "$HOME/.config/flai-google/label-plan.json"
```

The utility asks the official MCP server to validate the proposed label, displays the target account, manager ID when present, exact parameters and checksum, and asks you to type the displayed confirmation. Inspect everything before confirming. A mismatch or interruption stops the flow. Once a write is attempted, a timeout or error may leave its outcome uncertain: inspect the Google Ads account before trying again. The tool does not automatically retry. Protect the terminal output and plan because they contain account details.

## Existing scheduled Slack report

The existing landing-report component remains available through the [main README](../README.md). It directly reads GA4 on a server and sends to Slack; it does not use these MCP processes. The report's own service account, configuration, Slack token, scheduling and delivery state remain separate. Setting up AI connections does not change an existing scheduled report.
