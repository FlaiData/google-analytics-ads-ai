# GA4 landing reports to Slack

A self-hosted tool for reporting GA4 landing-page sessions and a selected event count to a Slack conversation, with threshold and failure alerts. Choose the pages, the event, the GA4 property, the reporting window, and the destination. The report compares the latest complete calendar days with the immediately preceding non-overlapping window of the same length.

The project queries the **Google Analytics Data API** directly. It can be used alongside an MCP server, but does not itself expose an MCP interface. It runs on infrastructure you control; no hosted service is included.

## What the numbers mean

For each configured landing path, **sessions** are GA4 sessions whose initial landing page matches that path. **Events** are GA4 `eventCount` for the configured event, grouped by the GA4 `landingPage` dimension. GA4 attribution and dimension compatibility depend on the property and should be validated; this does not establish that the event happened on the landing page. A session can contain multiple occurrences; event counts therefore are not counts of unique visitors, unique sessions with an event, conversions, revenue, or confirmed purchases. The report does not calculate a conversion rate from `eventCount`.

GA4 reporting can change after a day ends because of processing delays. A completed calendar day is not a promise of finalized data. Check the actual event implementation and GA4 definitions before drawing business conclusions. The query covers the whole GA4 property, including all streams: identical landing paths on different sites are combined. Use a property whose scope matches the report; stream or hostname filtering is not implemented. Only configured paths are reported; this tool does not automatically discover or map new pages. A valid report is not a claim that all relevant landing pages have been configured.

The application uses the configured IANA timezone and checks it against the GA4 property timezone. It rejects unexpected timezone, sampled, truncated or incomplete responses rather than silently delivering them. GA4 quotas and property permissions apply; reporting availability and aggregation depend on the underlying GA4 property.

## Requirements

- Docker with the Compose plugin, and an administrator who can configure a scheduler. Python installation instructions are below for local development.
- A Google Cloud project with the Analytics Data API enabled and a service account. Grant that service account read access to the intended GA4 property. Download a service-account JSON to a secure location outside the checkout; protect it as a password.
- A Slack app installed in the intended workspace and a bot token with `chat:write`. Add the bot to the intended channel and use its channel ID. Private channels require membership. Slack permissions for group direct messages are different; a bot is not automatically able to post to an existing group DM. Verify the actual token identity and destination before use.

Use a dedicated least-privilege identity. Never commit credentials, tokens, customer reports, actual IDs, or the local `.env` and `config.json`. The default `.gitignore` is a convenience, not a substitute for a review of files and Git history before sharing.

## First setup

Clone the repository on the host where the scheduler will run:

```sh
git clone https://github.com/FlaiData/ga4-landing-reports.git
cd ga4-landing-reports
```

```sh
cp config.example.json config.json
cp .env.example .env
chmod 600 config.json .env
```

Edit `config.json`:

- `report_id`: stable identifier for this report. Keep it unchanged across ordinary label, path, event, rule and formatting edits; changing it creates a separate delivery identity.
- `property_id`: your numeric GA4 property ID as a string.
- `timezone`: the GA4 property's IANA timezone, e.g. `America/New_York`.
- `days`: number of full days in each comparison window, from 1 to 365.
- `paths`: list of unique, absolute landing paths without query strings, each with a human-readable `label`. These are examples only; enter your own verified paths.
- `event_name`: the exact GA4 event name to count.
- `event_label`: an unambiguous display label for that event.
- `slack_channel_id`: ID of the intended Slack conversation.
- `state_dir`: writable storage for delivery records. Use `/data` with the included Compose setup.
- `alert_channel_id`: the Slack conversation for threshold and failure alerts. It may be the same as the report destination; the token identity needs access to both.
- `alert_rules`: a list of rules with `metric` (`sessions` or `events`), `direction` (`increase` or `decrease`), `percent`, and `min_previous`. Each rule is evaluated per configured landing path against the preceding window; e.g. a 30% decrease with `min_previous` 100 triggers only when the preceding value is at least 100. A zero previous value never triggers a percentage-based alert. An empty list disables threshold alerts.

Edit `.env` locally: set `GA4_CREDENTIALS_FILE` to the absolute path of the credential JSON and `SLACK_BOT_TOKEN` to the bot token. Restrict `.env`, the credential file and the checkout to trusted administrators. The container runs as UID 10001; ensure that identity can read the mounted credential file using appropriate file ownership or ACLs, while denying access to unrelated users. Do not make credentials world-readable. The config and credentials mounts are read-only; the named volume holds delivery state.

Build and test with fresh GA4 data without sending anything to Slack:

```sh
docker compose build
docker compose run --rm report --preview
```

Review the reported date ranges, timezone, landing paths and event labels, and verify that GA4 values match a known comparison in the GA4 interface. The preview makes live read requests to Google; it does not send a Slack message.

When the preview is correct and the Slack app has access to the intended destination:

```sh
docker compose run --rm report
```

Delivery uses a persistent state volume. Keep it across deployments and container recreations. The application reserves a reporting period before sending, records confirmed Slack timestamps, and refuses automatic resend when the delivery outcome is uncertain. Reports, threshold alerts and failure notifications have separate delivery keys. For the same report ID, property, window and channel, changing paths or labels does not cause a resend; changing report ID, property, window length, timezone or destination creates a new identity and can send again. A previously sent report is not resent after data or text changes. An incomplete or uncertain send requires checking the actual Slack conversation and the state before manually resolving it. Do not delete or reset the state merely to force a retry: a message might already have been posted.

## Schedule on a Linux host

This example runs twice weekly at 09:00 **in the explicitly specified timezone**. Replace `/srv/ga4-landings` with the actual absolute checkout path and choose the schedule and timezone suitable for the team. A systemd calendar timezone is independent of the GA4 reporting timezone.

`/etc/systemd/system/ga4-landings.service`:

```ini
[Unit]
Description=GA4 landing reports to Slack
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/srv/ga4-landings
ExecStart=/usr/bin/docker compose --project-directory /srv/ga4-landings run --rm report
TimeoutStartSec=45min
```

`/etc/systemd/system/ga4-landings.timer`:

```ini
[Unit]
Description=Scheduled GA4 landing report

[Timer]
OnCalendar=Mon,Thu *-*-* 09:00:00 America/New_York
Persistent=true
AccuracySec=1min
Unit=ga4-landings.service

[Install]
WantedBy=timers.target
```

Validate the calendar and service before enabling them:

```sh
systemd-analyze calendar 'Mon,Thu *-*-* 09:00:00 America/New_York'
systemd-analyze verify /etc/systemd/system/ga4-landings.service /etc/systemd/system/ga4-landings.timer
sudo systemctl daemon-reload
sudo systemctl enable --now ga4-landings.timer
systemctl list-timers --all ga4-landings.timer
```

`Persistent=true` can run a missed job when the host returns. The chosen timezone automatically follows that region's daylight-saving rules. Run only one scheduler for the same destination and state directory; independent installations with separate state can still duplicate a report.

## Monitoring and recovery

```sh
systemctl status ga4-landings.service --no-pager
journalctl -u ga4-landings.service -n 100 --no-pager
systemctl list-timers --all ga4-landings.timer
```

A failed run is visible in systemd and the journal. After loading a valid configuration, the application attempts a fixed-category failure notification to `alert_channel_id` once per period and error type, provided it has a token and functioning state storage. Threshold notifications use separate delivery state. The application does not send a recovery or all-clear notification; separate uptime monitoring is needed to detect missed runs. Alerts are **not guaranteed**: missing or invalid configuration, an unavailable token or state store, and a Slack outage can prevent them. The notification deliberately omits exception contents; consult the journal for diagnosis. For independent coverage, configure a separate monitoring system or a systemd `OnFailure=` service and verify that alerting path separately. Do not put tokens, private report contents or credentials into logs and alerts.

If Slack delivery times out or returns an ambiguous response, inspect the destination, delivery state and journal first. Confirm exactly which parts arrived before changing state or rerunning. A preview is useful for checking configuration but is not evidence of successful Slack delivery. If GA4 access, Slack access, timezone validation, data quality or the configured page roster needs attention, resolve the cause before a new production run.

## Updating safely

To learn about new versions, use GitHub's **Watch → Custom → Releases** on this repository. Runtime threshold and failure messages are delivered to the configured Slack alert channel; release notifications are separate. Review releases before updating: updates are not installed automatically.

1. Check the release notes and review changes. Back up your `config.json` and the Docker volume holding delivery state; preserve the credential and `.env` securely outside source control.
2. Test the new version in a separate checkout and state volume, with `--preview`; do not send test reports into the production destination. Reusing the production state volume from two simultaneous jobs can interfere with delivery.
3. Update the production checkout to the reviewed version, rebuild with `docker compose build`, and run a preview. Preserve the original named state volume and verify the actual Compose project name before replacing containers.
4. Check the timer, the next scheduled run and the journal. Never remove volumes as part of a routine update. If rolling back, preserve and reconcile the current state so a previously posted report is not repeated.

## Local development

Create a virtual environment, install the package with `pip install -e .`, and run the tests with `python -m unittest discover -s tests`. For local execution set `GOOGLE_APPLICATION_CREDENTIALS` to the secure credential path, set a writable local `state_dir` in a private config, and invoke `python -m landing_reports --config /path/to/config.json --preview`.

## Security and limitations

The GA4 credential can read whatever its account is granted; the Slack token can post wherever its app identity is allowed. Restrict both at the source and at rest, rotate them on suspected exposure, and do not paste them into issues or chat. Report content is business data: choose the Slack destination and host permissions accordingly. This project does not manage Google or Slack access, guarantee data freshness, attribute purchases, or automatically resolve uncertain delivery outcomes.

## Verification status

Automated tests exercise core behaviour without live Google or Slack calls. A real installation still needs its own preview, permission check and end-to-end verification in an authorized test destination before production scheduling.
