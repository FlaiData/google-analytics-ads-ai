# Read-only AI analysis prompts

These templates help an AI assistant use the separately installed official Google Analytics and Google Ads MCP servers. They are prompts, not an MCP server, an automatic scheduler, or a promise that the connected identity has access to a property. The templates do not modify GA4, Google Ads, Slack, or any other service and do not run on their own.

## Use a template

1. Connect the relevant read-only MCP server in your AI client using the repository's integration guide. Confirm that the profile belongs to the account you intend to analyze. A template cannot enforce permissions: use the read-only server configuration and least-privilege credentials.
2. Open a file below, copy its **Prompt** into your AI client, and replace each `<...>` placeholder with your own value. Do not paste passwords, tokens, or service-account JSON into the prompt.
3. Allow the assistant to inspect only the named property or customer. Review the actual tool responses, date windows, definitions, and data limitations before acting on recommendations.

| Prompt | Intended question |
| --- | --- |
| [GA4 landing-page analysis](ga4-landing-analysis.md) | How are my pages and selected event counts changing? |
| [Google Ads campaign performance](google-ads-campaign-performance.md) | Which campaigns are improving or deteriorating over 3 and 7 complete days? |
| [Combined Google Ads and GA4 analysis](combined-ads-ga4.md) | What can ad delivery and website behavior tell us together? |

The examples name tools as documented by Google. Your client may prefix or rename exposed tools; identify the equivalent read-only capability before running a query. GA4 event counts are not unique sessions with the event, completed purchases, or necessarily events that occurred on the landing page. Google Ads and GA4 use different attribution and conversion definitions; do not add platform-reported conversions together as unique sales. Current-day data, timezone mismatch, data processing delays, restricted data, sampling, and incomplete pagination can all change the interpretation.

Official tool references: [Google Analytics MCP](https://github.com/googleanalytics/google-analytics-mcp#tools-available), [Google Ads MCP](https://github.com/googleads/google-ads-mcp#tools--resources), and [Google Analytics Data API metadata](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/ResponseMetaData). Google's upstream tool names and capabilities may change; check the installed versions.
