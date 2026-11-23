# FlaiData Google Analytics & Ads — free and open source

Ask your local Codex or Claude Code assistant questions about your Google Analytics 4 and Google Ads data. The plugin supplies read-only Google MCP connections and a reporting skill. The plugin is free; third-party AI plans, Google services, access requirements, and quotas may apply. You use your own Google identities and credentials. Your data stays subject to your chosen services' policies.

## Set up Google access

You need Python 3.11+, a Google Cloud project with the appropriate API access, and access to your GA4 property and Google Ads account. Follow the detailed [Google connection guide](https://github.com/FlaiData/ga4-landing-reports/blob/main/docs/MCP_SETUP.md) through creating separate credentials and `~/.config/flai-google/profile.json`. Google Ads production access may require an application. Google authorization and access approval may require your administrator.

In a macOS or Linux terminal, install the pinned upstream MCP packages into a dedicated virtual environment:

```sh
mkdir -p "$HOME/.config/flai-google"
chmod 700 "$HOME/.config/flai-google"
python3 -m venv "$HOME/.config/flai-google/venv"
"$HOME/.config/flai-google/venv/bin/python" -m pip install 'analytics-mcp==1.1.0' 'google-ads-mcp==0.0.6'
```

Keep your private profile and credential files outside any repository with permissions `600`, and never paste their contents into an assistant. The guide explains how to obtain separate Google identities, configure the developer token, and create the profile. Both MCP servers use this local profile. This plugin currently supports macOS/Linux local execution; it does not run on remote or web clients without an equivalent environment.

## Install for Codex

```sh
codex plugin marketplace add https://github.com/FlaiData/ga4-landing-reports.git
codex plugin add flai-google@flaidata-google-tools
```

Alternatively open the project's marketplace in the Codex desktop Plugins directory and install FlaiData Google Insights. Start a fresh session. To refresh the marketplace use `codex plugin marketplace upgrade flaidata-google-tools`, then follow your Codex client's plugin update instructions. Existing plugins and credentials remain yours; do not overwrite their configuration.

## Install for Claude Code

```sh
claude plugin marketplace add FlaiData/ga4-landing-reports
claude plugin install flai-google@flaidata-google-tools
```

Restart Claude Code and use `/mcp` to check both connections. To update, run `claude plugin marketplace update flaidata-google-tools` followed by `claude plugin update flai-google@flaidata-google-tools`, and restart Claude Code.

## Try it

Ask: “Show the Google Ads campaigns I can access, then compare the last three full days against the preceding three full days.” Check the chosen account, dates, time zone and currency. Also ask: “Compare landing page traffic and conversion events in GA4 over the last seven full days.” Data interpretations and attribution differ between platforms.

The plugin does not change advertising campaigns or budgets and does not create scheduled Slack reports. The repository's separate GA4 Slack reporter is optional and requires its own setup and an always-on machine. A successful plugin install does not mean that Google's API or account permissions have been granted. No client credentials are included. This independent project is not endorsed by Google, OpenAI or Anthropic.
