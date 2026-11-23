# GA4 landing-page analysis

Use this when you want a read-only analysis of sessions and an existing GA4 event across selected landing pages. It uses the official Google Analytics MCP server, not the scheduled Slack reporter.

**Replace before use:** `<GA4_PROPERTY_ID>` is the numeric property ID, not a measurement ID beginning `G-`; `<LANDING_PATHS>` is a list of exact paths such as `/example-offer`; `<EVENT_NAME>` is an existing GA4 event such as `contact_click`; `<DAYS>` is a positive number such as 7.

## Prompt

```text
Act as an analytics specialist. This is READ ONLY: do not create or change events, dimensions, annotations, properties, advertising, credentials, destinations, or schedules. Do not send messages or create files in external systems.

Use only GA4 property <GA4_PROPERTY_ID>, landing paths <LANDING_PATHS>, and the existing event <EVENT_NAME>. First use the Analytics MCP account/property discovery tools, such as get_account_summaries and get_property_details, to verify the property identity and its reporting timezone; do not substitute another property if access fails.

Determine the latest <DAYS> fully completed calendar days in the GA4 property timezone and the immediately preceding non-overlapping <DAYS> calendar days. State the exact inclusive start and end dates and timezone. Exclude the current incomplete day. Use the Analytics MCP run_report capability to request GA4 sessions grouped by landingPage and, separately, eventCount for the exact event name grouped by landingPage for each window. Validate requested dimensions and metrics using available metadata and report only the supplied paths. Ensure that filters and periods match, paging is complete, and sampling, thresholding, '(other)' data loss, access restrictions or other incomplete-result indications are reported. If the API cannot validate compatibility or completeness, explain the limitation instead of inventing data.

For each path show both periods' sessions and eventCount, absolute changes and percentage changes. For a zero previous value write 'no baseline' rather than an invented percentage. Sort by current sessions and give a concise assessment of material increases and decreases, noting small samples and delays in GA4 processing. EventCount is the number of event occurrences, not people, unique sessions with an event, purchases, or necessarily an event on the landing page itself. Do not calculate a session conversion rate using eventCount. The GA4 property may include several streams or hosts with matching paths; indicate that the results may combine them unless a compatible filter is explicitly applied and verified. Flag mismatched names and paths as possible reasons for zero values, rather than asserting that no activity occurred.

End with at most three prioritized, evidence-based recommendations, each linked to the relevant numbers. If any item cannot be checked, say precisely what is unavailable. Do not claim causation or take action.
```

[Official Analytics MCP tools](https://github.com/googleanalytics/google-analytics-mcp#tools-available) · [GA4 API schema](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)
