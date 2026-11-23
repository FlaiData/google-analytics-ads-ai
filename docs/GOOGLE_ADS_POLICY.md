# Google Ads access and responsible use

This project is self-hosted software. Each user downloads and runs their own copy, uses their own Google Cloud project and Google Ads API access, and authorizes their own Google identity. It is not a hosted API, shared developer-access service, or shared credential proxy. This architecture does **not** by itself establish compliance with Google's requirements.

Read the current [Google Ads Developer Policies](https://support.google.com/adspolicy/answer/6169371?hl=en), particularly **Programmatic use**, before enabling an integration or providing it to others. Those policies distinguish software a user runs with their own credentials from hosted intermediaries that allow third parties to avoid obtaining their own Google Ads access. Google also requires end users to sign in manually to make account changes; never treat an AI prompt or a checksum by itself as proof of user consent or policy compliance.

Google Cloud project access level, permissible use, quota, account permissions and Google review requirements are separate from the local MCP tool configuration. The [current access-level documentation](https://developers.google.com/google-ads/api/docs/api-policy/access-levels) says Google Ads developer tokens were sunset on 9 September 2026; API access levels are assigned to a Cloud project. A newly enabled project starts with test access; production use requires an appropriate level such as Explorer or higher. Confirm requirements for your project in Google's current documentation. Some operations are restricted by access level.

[Required Minimum Functionality (RMF)](https://developers.google.com/google-ads/api/docs/api-policy/rmf) may apply based on access level, tool type and use. The reporting and analysis examples in this repository do not guarantee any RMF coverage or compliance. If you provide a tool to agencies or advertisers, or expand to create or manage functionality, verify applicable requirements and contact Google's compliance team where appropriate. Avoid reusing another party's developer access, Cloud project or OAuth identity to serve independent businesses.

## What this integration can and cannot do

The default configuration exposes only the official Ads MCP's reading tools: GAQL query, resource metadata and accessible customer listing. The OAuth `adwords` scope is broad; Google's API and account permissions remain the ultimate access boundary even when the MCP tool list is read-only. Use dedicated Google identities with the least account access possible.

The official Ads MCP also documents a propose/confirm workflow for a limited set of asset and label operations. Those tools are **not** complete campaign management; they do not establish a supported path in this project for changing campaign budgets, bids or statuses. A checksum binds parameters but is not a technical proof that a human gave informed consent. Never enable mutation tools in an autonomous agent and assume a checksum is a sufficient approval mechanism.

No changes are made by examples in this repository. Any future mutation capability requires a separately designed and independently reviewed human-authorization flow, Google's applicable policies, and explicit approval of each concrete change.
