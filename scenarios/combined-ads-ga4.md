# Combined Google Ads and GA4 analysis

Use this to investigate ad performance and website behavior together. It requires both official servers and separately authorized read-only profiles. The connections and accounts must be explicitly confirmed. Replace the placeholders with your own customer ID, numeric GA4 property ID, relevant landing paths, and a supported number of complete days. Never include tokens or credentials in the prompt.

## Prompt

```text
Act as a marketing analyst. This is READ ONLY: do not change advertising, analytics settings, conversion actions, attribution settings, budgets, bids, credentials, or any other configuration. Do not send messages or modify external systems. Your output is a report with recommendations only.

Analyze Google Ads customer <GOOGLE_ADS_CUSTOMER_ID> and GA4 property <GA4_PROPERTY_ID> for landing paths <LANDING_PATHS>. If needed, use <MANAGER_CUSTOMER_ID> only to access the target Ads customer. Verify names, IDs, currency, access, Ads customer timezone and GA4 property timezone before reporting. Use get_property_details and list_google_ads_links if available to examine the connection, and verify an Ads customer with the Google Ads MCP. If linking or identity cannot be confirmed, explain and do not claim the sources are linked; continue only with data whose ownership is confirmed. A GA4 Ads link does not itself prove every campaign is consistently tagged or attributed.

Compare the most recent <DAYS> complete calendar days with the previous <DAYS> complete days, separately in each source's reporting timezone. State the exact inclusive dates and timezone for both sources; if the timezones differ, warn that the windows have different actual boundaries even if calendar labels match. Avoid presenting them as exactly aligned without justified reconciliation. Check partial reporting, sampling, thresholds, data loss, data lag and complete pagination. State limitations; never invent missing metrics.

Use the Google Ads MCP search_search and metadata_get_resource_metadata read-only capabilities to report impressions, clicks, spend, customer currency and supported conversion metrics by relevant campaign. Fetch campaign status separately if needed to retain campaigns with no traffic. Use the GA4 MCP run_report and property metadata to report sessions, relevant session-scoped source/medium or channel, landingPage and a verified key event or eventCount as appropriate. Check available metrics and compatible dimensions/filters before querying. Do not describe eventCount as unique converting sessions, sales, or necessarily a click on the landing page. Indicate whether a GA4 source field is session-scoped or first-user-scoped; do not compare or sum unlike scopes.

Show each platform's values and changes separately, with dates, units, absolute differences and percentage changes; use 'no baseline' when the earlier value is zero. Compare campaign-to-landing relationships only when the available identifiers, destination URLs, tagging and GA4 attribution substantiate them. Otherwise explain the limitation and describe cross-source observations as hypotheses. Ads clicks and GA4 sessions are different measures; Google Ads conversions and GA4 key events can differ in attribution windows, counting, identity and definitions. Do not add them together as unique outcomes or claim one source proves the other's sales. Do not infer cause from correlation.

Provide a short findings table, a list of data-quality gaps, and up to three prioritized checks or recommendations. If either source is unavailable, clearly identify it and provide only the supported part of the analysis. Do not apply changes.
```

[Google Analytics MCP](https://github.com/googleanalytics/google-analytics-mcp#tools-available) · [Google Ads MCP](https://github.com/googleads/google-ads-mcp#tools--resources) · [GA4 attribution](https://support.google.com/analytics/answer/10597962)
