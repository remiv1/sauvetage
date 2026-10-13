# Rapport des Tests - pytest tests

**Date:** 2026-10-13T09:49:09.048674+02:00
**Suite:** pytest tests

---

## Summary

| Metric | Value |
| ------ | ----- |
| **Status** | ✅ ALL TESTS PASSED |
| **Total Tests** | 251 |
| **Passed** | ✅ 251 |
| **Failed** | ❌ 0 |
| **Skipped** | ⊘ 0 |
| **Pass Rate** | 100.0% |

---

## Detailed Results

| Test Class | Test Name | Status | Time (s) |
| ---------- | --------- | ------ | -------- |
| tests.db_objects.customers | customer_create_read_and_update | ✅ PASSED | 0.186 |
| tests.db_objects.customers | create_complete_customer | ✅ PASSED | 0.041 |
| tests.db_objects.henrri_addresses | address_payload_contains_city_and_post_code | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_addresses | address_payload_handles_missing_second_line | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_addresses | address_payload_omits_id_when_not_synced | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_addresses | address_payload_rejects_incomplete_address[city-ville] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_addresses | address_payload_rejects_incomplete_address[postal_code-co... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_addresses | address_payload_rejects_incomplete_address[address_line1-... | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_addresses | customer_uses_active_billing_address | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_addresses | customer_prefers_complete_active_billing_address | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_addresses | customer_without_active_billing_address_raises | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_reads_credit_limit[None-200] | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_reads_credit_limit[20-20] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_reads_credit_limit[500-500] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_rejects_invalid_credit_limit[] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_rejects_invalid_credit_limit[0] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_rejects_invalid_credit_limit[-1] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_rejects_invalid_credit_limit[20.5] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | monthly_limit_rejects_invalid_credit_limit[invalide] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | reservation_uses_atomic_shared_budget | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | cancellation_does_not_consume_credit | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | calendar_month_seed_is_not_carried_forward[10-27-2026-11] | ✅ PASSED | 0.007 |
| tests.db_objects.henrri_monthly_credits | calendar_month_seed_is_not_carried_forward[11-0-2026-12] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | calendar_month_seed_is_not_carried_forward[12-0-2027-1] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | exhausted_or_reserved_budget_blocks_new_invoice[200-tokens0] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | exhausted_or_reserved_budget_blocks_new_invoice[199-tokens1] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | unavailable_mongo_blocks_reservation | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | inflight_success_stays_in_original_month | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | invalid_configuration_blocks_monthly_quota[0--0] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | invalid_configuration_blocks_monthly_quota[-1--0] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | invalid_configuration_blocks_monthly_quota[200--1] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | invalid_configuration_blocks_monthly_quota[200-2026-1-0] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | invalid_configuration_blocks_monthly_quota[200-2026-13-0] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | invalid_configuration_blocks_monthly_quota[200-2026-10-201] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | read_and_auth_do_not_use_monthly_credit[GET-/v1/items] | ✅ PASSED | 0.005 |
| tests.db_objects.henrri_monthly_credits | read_and_auth_do_not_use_monthly_credit[HEAD-/v1/document... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | read_and_auth_do_not_use_monthly_credit[POST-/v1/users/au... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | read_and_auth_do_not_use_monthly_credit[POST-/v1/users/re... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[200-POST] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[200-PUT] | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[200-PATCH] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[200-DELETE] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[201-POST] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[201-PUT] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[201-PATCH] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[201-DELETE] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[204-POST] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[204-PUT] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[204-PATCH] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[204-DELETE] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[400-POST] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[400-PUT] | ✅ PASSED | 0.005 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[400-PATCH] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[400-DELETE] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[429-POST] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[429-PUT] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[429-PATCH] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[429-DELETE] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[500-POST] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[500-PUT] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[500-PATCH] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | business_write_settles_its_reservation[500-DELETE] | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | transport_failure_preserves_uncertain_credit[ConnectError... | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | transport_failure_preserves_uncertain_credit[ConnectTimeo... | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_monthly_credits | transport_failure_preserves_uncertain_credit[PoolTimeout-... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | transport_failure_preserves_uncertain_credit[ReadTimeout-... | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_monthly_credits | transport_failure_preserves_uncertain_credit[ReadError-Fa... | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_monthly_credits | transport_failure_preserves_uncertain_credit[WriteError-F... | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_monthly_credits | transport_failure_preserves_uncertain_credit[WriteTimeout... | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | blocked_credit_prevents_http_write[error0] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | blocked_credit_prevents_http_write[error1] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | confirmation_failure_preserves_successful_remote_id | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_monthly_credits | invoice_flow_stops_before_customer_and_product_writes | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | quota_check_closes_temporary_service | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | invoice_order_does_not_create_local_invoice_when_quota_ex... | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_monthly_credits | invoice_order_preserves_partial_invoice_when_last_credit_... | ✅ PASSED | 0.005 |
| tests.db_objects.henrri_monthly_credits | retry_commits_remote_ids_when_monthly_quota_blocks_remain... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_monthly_credits | sdk_applies_minute_and_monthly_limits_to_actual_http_tran... | ✅ PASSED | 0.096 |
| tests.db_objects.henrri_monthly_credits | calendar_uses_utc_not_local_first_of_month | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_monthly_credits | mongodb_concurrent_reservations_and_month_rollover | ✅ PASSED | 2.492 |
| tests.db_objects.henrri_payloads | henrri_quota_reads_environment[None-20] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henrri_quota_reads_environment[20-20] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | henrri_quota_reads_environment[60-60] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henrri_quota_rejects_invalid_configuration[] | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | henrri_quota_rejects_invalid_configuration[0] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henrri_quota_rejects_invalid_configuration[-1] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henrri_quota_rejects_invalid_configuration[20/minute] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henrri_quota_rejects_invalid_configuration[invalide] | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henrri_quota_waits_and_rechecks_before_sending | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_payloads | henrri_quota_enforces_moving_window_across_two_workers | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | henrri_quota_blocks_when_shared_storage_is_unavailable | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | henrri_services_share_mongodb_quota | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_payloads | henrri_http_counts_authentication_and_business_requests | ✅ PASSED | 0.022 |
| tests.db_objects.henrri_payloads | henrri_http_does_not_send_when_quota_storage_fails | ✅ PASSED | 0.018 |
| tests.db_objects.henrri_payloads | customer_to_dict_henrri_contract_for_professional | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | customer_to_dict_henrri_normalizes_empty_professional_vat... | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | customer_to_dict_henrri_contract_for_individual | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | customer_to_dict_henrri_includes_id_for_update | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | customer_to_dict_henrri_omits_contact_when_requested | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | invoice_to_dict_henrri_contract | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | henri_product_contract | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_payloads | henri_product_contract_uses_zero_when_price_is_missing | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henri_invoice_line_contract_omits_totals_when_tax_is_excl... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | henri_shipping_fee_line_uses_synchronized_product_id | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henri_shipping_fee_synchronizes_product_on_first_use | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | henri_service_configures_http_timeout | ✅ PASSED | 0.016 |
| tests.db_objects.henrri_payloads | henri_invoice_orchestrates_customer_product_and_document | ✅ PASSED | 0.009 |
| tests.db_objects.henrri_payloads | create_invoice_does_not_send_lines_when_creating_henrri_d... | ✅ PASSED | 0.006 |
| tests.db_objects.henrri_payloads | retry_henrri_invoice_is_idempotent_when_remote_document_i... | ✅ PASSED | 0.005 |
| tests.db_objects.henrri_payloads | sync_invoice_with_henrri_logs_failed_status_when_sync_fails | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_payloads | customer_partners_push_uses_partner_sync_for_both_targets | ✅ PASSED | 0.007 |
| tests.db_objects.henrri_payloads | customer_partners_push_returns_http_error_when_sync_fails | ✅ PASSED | 0.004 |
| tests.db_objects.henrri_payloads | order_wc_push_returns_http_error_when_sync_fails | ✅ PASSED | 0.005 |
| tests.db_objects.henrri_payloads | invoice_order_rejects_already_fully_invoiced_order | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_payloads | check_product_returns_true_when_item_exists_in_henrri | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_payloads | check_customer_returns_false_when_customer_lookup_fails | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | create_invoice_updates_known_customer_product_and_document | ✅ PASSED | 0.009 |
| tests.db_objects.henrri_payloads | create_invoice_leaves_finalized_remote_document_untouched | ✅ PASSED | 0.006 |
| tests.db_objects.henrri_upsert | upsert_customer_creates_when_identifier_is_unknown | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_upsert | upsert_customer_updates_when_identifier_is_known | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_upsert | upsert_product_creates_then_updates | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_upsert | upsert_product_logs_payload_before_remote_call | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_upsert | sync_customer_persists_all_returned_identifiers | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_upsert | sync_customer_sends_full_address | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_upsert | sync_customer_updates_contact_separately | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_upsert | sync_customer_passes_known_identifier_for_update | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_upsert | sync_product_persists_returned_identifier | ✅ PASSED | 0.002 |
| tests.db_objects.inventory | multiple_prices_can_have_distinct_vat_rates | ✅ PASSED | 0.025 |
| tests.db_objects.inventory | order_line_is_split_for_multiple_valid_prices | ✅ PASSED | 0.068 |
| tests.db_objects.inventory | multi_price_order_can_be_invoiced_and_shipped_by_split_lines | ✅ PASSED | 0.139 |
| tests.db_objects.inventory | add_movements | ✅ PASSED | 0.033 |
| tests.db_objects.objects | object_create_read_and_update | ✅ PASSED | 0.068 |
| tests.db_objects.objects | get_by_ref_finds_existing_object_even_when_inactive | ✅ PASSED | 0.138 |
| tests.db_objects.order_shipping_fee | shipping_fee_is_allocated_by_discounted_amount_before_tax | ✅ PASSED | 0.001 |
| tests.db_objects.order_shipping_fee | shipping_fee_rounding_remainder_is_kept | ✅ PASSED | 0.001 |
| tests.db_objects.order_shipping_fee | shipping_fee_is_optional | ✅ PASSED | 0.001 |
| tests.db_objects.order_shipping_fee | shipping_fee_uses_negative_quantity_for_credit_note | ✅ PASSED | 0.001 |
| tests.db_objects.order_shipping_fee | invoice_order_flushes_shipping_order_lines_before_invoice... | ✅ PASSED | 0.008 |
| tests.db_objects.order_shipping_fee | ship_order_rejects_shipping_fee_line | ✅ PASSED | 0.002 |
| tests.db_objects.order_shipping_fee | shipping_fee_does_not_make_order_partially_shipped | ✅ PASSED | 0.002 |
| tests.db_objects.orders | cancel_order_cancels_lines_and_releases_reservations | ✅ PASSED | 0.002 |
| tests.db_objects.orders | create_order_with_invoice_and_shipment | ✅ PASSED | 0.082 |
| tests.db_objects.users | user_to_dict | ✅ PASSED | 0.031 |
| tests.db_objects.users | user_from_dict | ✅ PASSED | 0.001 |
| tests.db_objects.users | complete_user | ✅ PASSED | 0.017 |
| tests.db_objects.woo_payloads | wc_customer_sync_links_existing_customer_by_email | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_customer_sync_creates_and_links_missing_customer | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | customer_repository_updates_partner_identifiers | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads | general_object_payload_uses_wc_tax_slug | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads | metadata_payload_uses_woo_attribute_shape | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | book_payload_keeps_woo_attribute_keys | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | other_object_payload_has_empty_attributes | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | variation_payload_uses_wc_keys | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | object_tag_payload_uses_wc_tag_id | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | wc_product_payload_includes_synced_tags | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads | update_product_syncs_missing_wc_tags_before_export | ✅ PASSED | 0.011 |
| tests.db_objects.woo_payloads | order_line_payload_uses_wc_tax_class_and_variation_id | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | order_line_payload_raises_clear_error_when_product_not_sy... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_product_payload_builds_catalog_payload_with_merged_att... | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads | wc_diff_objects_detects_create_update_and_delete_batches | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads | order_payload_uses_wc_customer_and_line_contract | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads | cancelled_order_payload_removes_known_lines | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads | order_payload_exports_shipping_fee_in_fee_lines | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads | wc_orders_service_stores_fee_line_identifier | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | imported_shipping_fee_is_converted_to_fee_line | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_orders_service_replaces_shipping_identifier_with_fee_i... | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | returned_order_payload_uses_refunded_status | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | match_line_to_wc_uses_product_and_variation_ids | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | wc_orders_service_uses_customer_woo_email_and_remote_cust... | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads | wc_orders_service_creates_missing_remote_customer_when_lo... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads | wc_orders_service_preserves_existing_line_ids | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | wc_product_update_fails_when_woo_returns_no_wc_id | ✅ PASSED | 0.007 |
| tests.db_objects.woo_payloads | wc_product_build_media_src_uses_internal_public_host_when... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads | woo_media_route_resolves_media_by_id_and_serves_file | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_product_build_media_src_uses_token_for_absolute_local_... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | woo_media_route_uses_basename_for_local_file | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads | woo_media_route_serves_existing_absolute_local_file | ✅ PASSED | 0.007 |
| tests.db_objects.woo_payloads | woo_media_route_detects_real_mime_from_file_content | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads | wc_orders_service_creates_missing_products_before_push | ✅ PASSED | 0.070 |
| tests.db_objects.woo_payloads | wc_orders_service_push_order_updates_remote_order_and_log... | ✅ PASSED | 0.007 |
| tests.db_objects.woo_payloads | customer_payload_and_repo_match_woo_customer_id | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.customers | customer_payload_and_repo_match_woo_customer_id | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.customers | professional_customer_payload_uses_string_names | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.media | wc_product_build_media_src_uses_internal_public_host_when... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.media | wc_product_build_media_src_uses_token_for_absolute_local_... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.media | woo_media_route_resolves_media_by_id_and_serves_file | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.media | woo_media_route_uses_basename_for_local_file | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.media | woo_media_route_serves_existing_absolute_local_file | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.media | woo_media_route_detects_real_mime_from_file_content | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.orders | order_line_payload_uses_wc_tax_class_and_variation_id | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.orders | order_line_payload_raises_clear_error_when_product_not_sy... | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.orders | order_payload_uses_wc_customer_and_line_contract | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_uses_customer_woo_email_and_remote_cust... | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_creates_missing_remote_customer_when_lo... | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_preserves_existing_line_ids | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_creates_missing_products_before_push | ✅ PASSED | 0.008 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_push_order_updates_remote_order_and_log... | ✅ PASSED | 0.007 |
| tests.db_objects.woo_payloads.orders | push_recent_local_orders_includes_commands_already_linked... | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | product_metadata_exports_weight_and_dimensions[110-110_0] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_exports_weight_and_dimensions[110-110_1] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_exports_weight_and_dimensions[weight2-11... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_exports_weight_and_dimensions[0-0] | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[None] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[] | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[invalide] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[-1] | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[True] | ✅ PASSED | 0.007 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[NaN] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[Infinity] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_weight[weight7] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[None] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[246*217] | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[246*217*24*1] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[246**24] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[246*invalide*24] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[246*-217*24] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[246*NaN*24] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_metadata_omits_invalid_dimensions[dimensions8] | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | product_without_measurements_omits_shipping_fields[None] | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_without_measurements_omits_shipping_fields[metada... | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | product_export_commits_first_batch_before_second_fails | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | product_export_keeps_successful_items_of_failed_batch | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | product_sku_conflict_is_reconciled_and_updated | ✅ PASSED | 0.008 |
| tests.db_objects.woo_payloads.products | product_sku_conflict_without_unique_match_remains_error[r... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_sku_conflict_without_unique_match_remains_error[r... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_sku_conflict_without_unique_match_remains_error[r... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | product_sku_conflict_without_unique_match_remains_error[r... | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | product_reconciliation_read_failure_remains_error | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | invalid_product_return_does_not_report_success[item0] | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | invalid_product_return_does_not_report_success[item1] | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | invalid_product_return_does_not_report_success[item2] | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | reconciled_product_id_survives_failed_update | ✅ PASSED | 0.007 |
| tests.db_objects.woo_payloads.products | single_product_is_found_by_sku_before_creation | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | single_product_with_existing_id_does_not_hide_update_error | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | invalid_remote_catalog_is_rejected[payload0] | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | invalid_remote_catalog_is_rejected[invalid] | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | product_batches_are_limited_and_reconcile_existing_sku | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads.products | general_object_payload_uses_wc_tax_slug | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | object_tag_payload_uses_wc_tag_id | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | wc_product_payload_includes_synced_tags | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | update_product_syncs_missing_wc_tags_before_export | ✅ PASSED | 0.010 |
| tests.db_objects.woo_payloads.products | book_payload_keeps_woo_attribute_keys | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | other_object_payload_has_empty_attributes | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | variation_payload_uses_wc_keys | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | wc_parent_payload_declares_variation_attribute | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | wc_product_variations_are_reconciled | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | wc_diff_objects_detects_create_update_and_delete_batches | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | wc_product_builds_catalog_payload_with_merged_attributes | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | wc_product_update_fails_when_woo_returns_no_wc_id | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | match_line_to_wc_uses_product_and_variation_ids | ✅ PASSED | 0.001 |

---

*Generated on 2026-10-13 09:49:15*
