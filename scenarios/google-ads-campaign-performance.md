# Google Ads campaign performance: 3 and 7 days

Use this for a read-only Google Ads review. It does not publish or modify campaigns. Replace `<GOOGLE_ADS_CUSTOMER_ID>` with the intended customer ID; if access is through a manager, supply `<MANAGER_CUSTOMER_ID>` separately when needed. Do not use credentials or tokens as prompt values.

## Prompt

```text
Act as a Google Ads analyst. This is READ ONLY: do not create, edit, pause, enable, remove, publish, or otherwise mutate any campaign, ad group, keyword, conversion, budget, bid, asset, label, or account setting. Do not send messages or write to external services. Provide recommendations only.

Review only Google Ads customer <GOOGLE_ADS_CUSTOMER_ID>. If applicable, use manager customer <MANAGER_CUSTOMER_ID> only as the login customer; it is not the target account. First verify the accessible customer and use a read-only Google Ads query to obtain the customer name, ID, currency, timezone and whether it is a manager. If the intended account cannot be identified or accessed, stop; never replace it with a similarly named account.

In the customer's timezone, compare the latest 3 complete calendar days with the previous 3 complete days, and the latest 7 complete calendar days with the previous 7 complete days. State each exact inclusive date range, timezone, currency, and the time checked. Exclude the current incomplete day. Use the Google Ads MCP read-only tools: customers_list_accessible_customers, metadata_get_resource_metadata as needed, and search_search with valid GAQL. Tool prefixes may differ in this client.

Fetch current campaign identity, configured status, serving/primary status and available primary status reasons separately from performance, so enabled or paused campaigns with zero impressions are not silently omitted. Then query comparable account and campaign performance for each window. Use supported fields to show impressions, clicks, cost, CTR, average CPC, conversions, cost per conversion, conversion value and ROAS where available and meaningful. Convert cost_micros to the account currency by dividing by 1,000,000; recompute aggregate ratios from totals rather than averaging row-level rates. Validate fields, date boundaries and complete results, and identify any campaigns with no baseline or inaccessible data.

For the account and each relevant campaign present both values, absolute differences, percentage differences and current status. If the prior value is zero, show 'no baseline' rather than dividing by zero. For CTR and other rates, show percentage-point changes as well. Explain which campaigns appear better, worse or inconclusive for their stated objectives, and cite both volume and efficiency. Include paused or limited campaigns and reasons only when the API actually returns them. State that conversions can arrive late, definitions vary by configured conversion action and campaign objective, and an observed change does not prove causation. Do not call a conversion a ticket sale or a lead unless the conversion action confirms it. Do not infer exact time or reason for a status change from the current status alone.

End with up to five specific, prioritized recommendations; explain the evidence and uncertainty for each. Do not implement them.
```

[Official Google Ads MCP tools](https://github.com/googleads/google-ads-mcp#tools--resources) · [GAQL reference](https://developers.google.com/google-ads/api/docs/query/overview)
