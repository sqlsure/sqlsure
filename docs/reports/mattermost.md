# sqlsure scan report — /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw
*2026-07-01 · rulebook from schema .yml files (2 project(s)) · dialect: snowflake*

## Rulebook coverage
- models in rulebook: **355**, with declared grain: **92** (25%)
- declared join edges: **17**
- joins seen in SQL: **128** — verifiable: **0**, between known tables but undeclared: **45**, involving unknown tables/CTE output: **83**

## SQL scanned
- files: **489**, parsed: **206**, skipped (jinja/parse): **283**

## Violations — 0 errors, 41 warnings, 0 policy

| rule | count |
|---|---|
| UNDECLARED_JOIN | 41 |

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/licenses/_licenses_servers/int_cloud_licenses.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_stripe__subscriptions and stg_stripe__customers — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_stripe__subscriptions and stg_stripe__products — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/licenses/_licenses_servers/int_self_hosted_licenses.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_stripe__subscriptions and stg_stripe__customers — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_stripe__subscriptions and stg_stripe__products — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_cws__license and stg_stripe__products — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/licenses/int_known_licenses.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__account — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/licenses/int_latest_server_customer_info.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_stripe__subscriptions and stg_stripe__customers — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_stripe__subscriptions and stg_stripe__products — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/servers/_excludable_servers/int_excludable_servers_cloud_installations.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between _int_server_installation_id_bridge and stg_stripe__subscriptions — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between _int_server_installation_id_bridge and stg_stripe__customers — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/sales/hightouch/int_account_arr_seats.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__opportunity_line_item — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity_line_item and stg_salesforce__opportunity — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity_line_item and stg_salesforce__account — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__account and stg_salesforce__opportunity — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__account and stg_salesforce__opportunity_line_item — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__account and stg_salesforce__product2 — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/sales/hightouch/int_opportunity_ext.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__contact — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__lead — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__opportunity_line_item — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__user — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__account — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/sales/hightouch/int_opportunity_line_item_daily_arr.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity_line_item and stg_salesforce__opportunity — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/sales/int_onprem_trial_license_information.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_cws__trial_request_licenses and stg_mm_telemetry_prod__license — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/product/boards/dim_board_customers.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between _int_server_installation_id_bridge and stg_stripe__subscriptions — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between _int_server_installation_id_bridge and stg_stripe__customers — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/product/dim_server_info.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_stripe__subscriptions and stg_stripe__customers — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/product/notifications/fct_notification_stats.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between notification_date_hour and int_notifications_eu_hourly — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between notification_date_hour and int_notifications_us_hourly — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between notification_date_hour and int_notifications_test_hourly — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between notification_date_hour and int_notifications_logs_eu_hourly — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between notification_date_hour and int_notifications_logs_us_hourly — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between notification_date_hour and int_notifications_logs_test_hourly — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/product/nps/fct_nps_feedback.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between int_nps_feedback and int_nps_score — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/product/rpt_tedau_at_day_28.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between fct_active_users and dim_daily_server_info — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/sales/fct_subscription_history.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_cws__subscription_history and stg_stripe__subscriptions — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_cws__subscription_history and stg_stripe__products — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/sales/hightouch/sync_account_arr_and_type.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__account and stg_salesforce__account — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/marts/sales/hightouch/sync_lead_account_link.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__lead and stg_salesforce__account — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/reports/product/active_user_base/rpt_active_user_base.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between fct_active_users and dim_excludable_servers — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/reports/product/customers/rpt_current_customers.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__account — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

### /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/reports/product/mme/rpt_won_opportunities.sql
- **[warning] UNDECLARED_JOIN** — No declared relationship between stg_salesforce__opportunity and stg_salesforce__account — cardinality is unknown, so aggregates cannot be verified.
  - fix: Declare the join (cardinality + keys) in the semantic model, or route through a declared path.

## Skipped files (best-effort jinja strip failed)
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/data_eng/geoip/int_ip_country_lookup.sql — `Invalid expression / Unexpected token. Line 2, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/active_users/int_user_active_days_legacy_telemetry.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/active_users/int_user_active_days_mobile_telemetry.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/active_users/int_user_active_days_server_telemetry.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/active_users/int_user_active_days_spined.sql — `Invalid expression / Unexpected token. Line 5, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/boards_active_users/int_boards_active_days_spined.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/boards_active_users/int_boards_client_active_days.sql — `Invalid expression / Unexpected token. Line 2, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/boards_active_users/int_boards_client_telemetry_daily.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/calls_active_users/int_calls_active_days_spined.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/calls_active_users/int_calls_client_active_days.sql — `Invalid expression / Unexpected token. Line 2, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/calls_active_users/int_calls_client_telemetry_daily.sql — `Invalid expression / Unexpected token. Line 3, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mattermost2__config_ldap.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mattermost2__config_oauth.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mattermost2__config_plugin.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mattermost2__config_saml.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mattermost2__config_service.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mm_telemetry_prod__config_ldap.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mm_telemetry_prod__config_oauth.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mm_telemetry_prod__config_plugin.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mm_telemetry_prod__config_saml.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mm_telemetry_prod__config_service.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/configs/int_mm_telemetry_prod__configs.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/calls/int_calls_daily_usage_per_user.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/copilot/int_copilot_daily_usage_per_user.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/int_daily_usage_per_user_full.sql — `Invalid expression / Unexpected token. Line 13, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/int_feature_daily_spine.sql — `Invalid expression / Unexpected token. Line 6, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/mattermost/int_client_feature_attribution.sql — `Invalid expression / Unexpected token. Line 9, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/mattermost/int_feature_daily_usage_per_user.sql — `Invalid expression / Unexpected token. Line 8, Col: 4.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/mattermost/int_mattermost_feature_attribution.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- /private/tmp/claude-501/-Users-tejusarora-aie-demo/86941770-a533-494f-b879-eced4c1e2e60/scratchpad/mattermost-dw/transform/mattermost-analytics/models/intermediate/product/features/mattermost/int_server_feature_attribution.sql — `Invalid expression / Unexpected token. Line 3, Col: 6.`
- … and 253 more