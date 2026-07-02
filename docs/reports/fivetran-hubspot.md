# sqlsure scan report — /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot
*2026-07-01 · rulebook from schema .yml files (2 project(s)) · dialect: default*

## Rulebook coverage
- models in rulebook: **90**, with declared grain: **5** (5%)
- declared join edges: **0**
- joins seen in SQL: **0** — verifiable: **0**, between known tables but undeclared: **0**, involving unknown tables/CTE output: **0**

## SQL scanned
- files: **190**, parsed: **73**, skipped (jinja/parse): **117**

## Violations — 0 errors, 0 warnings, 0 policy

## Skipped files (best-effort jinja strip failed)
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/intermediate/int_hubspot__owners_enhanced.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/history/hubspot__contact_history.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/hubspot__contact_lists.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/hubspot__contacts.sql — `Invalid expression / Unexpected token. Line 7, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/hubspot__email_campaigns.sql — `Invalid expression / Unexpected token. Line 4, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/hubspot__email_sends.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/intermediate/int_hubspot__contact_merge_adjust.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/intermediate/int_hubspot__email_aggregate_status_change.sql — `Invalid expression / Unexpected token. Line 4, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/intermediate/int_hubspot__email_event_aggregates.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/intermediate/int_hubspot__email_metrics__by_contact_list.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/intermediate/int_hubspot__engagement_metrics__by_contact.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/marketing/intermediate/int_hubspot__form_metrics__by_contact.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/sales/history/hubspot__company_history.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/sales/history/hubspot__deal_history.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/sales/hubspot__companies.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/sales/hubspot__deal_stages.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/sales/hubspot__deals.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/sales/hubspot__engagements.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/sales/intermediate/int_hubspot__deals_enhanced.sql — `Invalid expression / Unexpected token. Line 5, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/service/hubspot__daily_ticket_history.sql — `Invalid expression / Unexpected token. Line 5, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/service/hubspot__tickets.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/service/intermediate/int_hubspot__daily_ticket_history.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/service/intermediate/int_hubspot__pivot_daily_ticket_history.sql — `Invalid expression / Unexpected token. Line 5, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/service/intermediate/int_hubspot__scd_daily_ticket_history.sql — `Invalid expression / Unexpected token. Line 5, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/service/intermediate/int_hubspot__ticket_calendar_spine.sql — `Invalid expression / Unexpected token. Line 4, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/staging/stg_hubspot__company.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/staging/stg_hubspot__company_property_history.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/staging/stg_hubspot__contact.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/staging/stg_hubspot__contact_form_submission.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/dbt_hubspot/models/staging/stg_hubspot__contact_list.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- … and 87 more