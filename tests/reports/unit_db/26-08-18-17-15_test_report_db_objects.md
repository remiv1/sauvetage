# Rapport des Tests - pytest tests

**Date:** 2026-08-18T17:15:54.574142
**Suite:** pytest tests

---

## Summary

| Metric | Value |
| ------ | ----- |
| **Status** | ✅ ALL TESTS PASSED |
| **Total Tests** | 0 |
| **Passed** | ✅ 0 |
| **Failed** | ❌ 0 |
| **Skipped** | ⊘ 0 |
| **Pass Rate** | 0.0% |

---

## Detailed Results

| Test Class | Test Name | Status | Time (s) |
| ---------- | --------- | ------ | -------- |
| tests.db_objects.customers | customer_create_read_and_update | ✅ PASSED | 0.106 |
| tests.db_objects.customers | create_complete_customer | ✅ PASSED | 0.027 |
| tests.db_objects.henrri_payloads | customer_to_dict_henrri_contract_for_professional | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | customer_to_dict_henrri_contract_for_individual | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | invoice_to_dict_henrri_contract | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henri_product_contract | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henri_invoice_line_contract_omits_totals_when_tax_is_excl... | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | henri_service_configures_http_timeout | ✅ PASSED | 0.157 |
| tests.db_objects.henrri_payloads | henri_invoice_orchestrates_customer_product_and_document | ✅ PASSED | 0.006 |
| tests.db_objects.henrri_payloads | create_invoice_does_not_send_lines_when_creating_henrri_d... | ✅ PASSED | 0.005 |
| tests.db_objects.henrri_payloads | retry_henrri_invoice_is_idempotent_when_remote_document_i... | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | sync_invoice_with_henrri_logs_failed_status_when_sync_fails | ✅ PASSED | 0.002 |
| tests.db_objects.henrri_payloads | customer_wc_push_returns_http_error_when_sync_fails | ✅ PASSED | 0.010 |
| tests.db_objects.henrri_payloads | order_wc_push_returns_http_error_when_sync_fails | ✅ PASSED | 0.003 |
| tests.db_objects.henrri_payloads | invoice_order_rejects_already_fully_invoiced_order | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | check_product_returns_true_when_item_exists_in_henrri | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | check_customer_returns_false_when_customer_lookup_fails | ✅ PASSED | 0.001 |
| tests.db_objects.henrri_payloads | create_invoice_reuses_existing_remote_customer_and_product | ✅ PASSED | 0.004 |
| tests.db_objects.inventory | multiple_prices_can_have_distinct_vat_rates | ✅ PASSED | 0.068 |
| tests.db_objects.inventory | order_line_is_split_for_multiple_valid_prices | ✅ PASSED | 0.039 |
| tests.db_objects.inventory | multi_price_order_can_be_invoiced_and_shipped_by_split_lines | ✅ PASSED | 0.389 |
| tests.db_objects.inventory | add_movements | ✅ PASSED | 0.018 |
| tests.db_objects.objects | object_create_read_and_update | ✅ PASSED | 0.041 |
| tests.db_objects.objects | get_by_ref_finds_existing_object_even_when_inactive | ✅ PASSED | 0.022 |
| tests.db_objects.orders | create_order_with_invoice_and_shipment | ✅ PASSED | 0.041 |
| tests.db_objects.users | user_to_dict | ✅ PASSED | 0.023 |
| tests.db_objects.users | user_from_dict | ✅ PASSED | 0.000 |
| tests.db_objects.users | complete_user | ✅ PASSED | 0.011 |
| tests.db_objects.woo_payloads | general_object_payload_uses_wc_tax_slug | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | metadata_payload_uses_woo_attribute_shape | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads | book_payload_keeps_woo_attribute_keys | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads | other_object_payload_has_empty_attributes | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads | variation_payload_uses_wc_keys | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads | object_tag_payload_uses_wc_tag_id | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | wc_product_payload_includes_synced_tags | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | update_product_syncs_missing_wc_tags_before_export | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads | order_line_payload_uses_wc_tax_class_and_variation_id | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | order_line_payload_raises_clear_error_when_product_not_sy... | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | wc_product_payload_builds_catalog_payload_with_merged_att... | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | wc_diff_objects_detects_create_update_and_delete_batches | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | order_payload_uses_wc_customer_and_line_contract | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | match_line_to_wc_uses_product_and_variation_ids | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads | wc_orders_service_uses_customer_woo_email_and_remote_cust... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_orders_service_creates_missing_remote_customer_when_lo... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_orders_service_syncs_line_ids_from_wc_payload | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads | wc_product_update_fails_when_woo_returns_no_wc_id | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads | wc_product_build_media_src_uses_internal_public_host_when... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | woo_media_route_resolves_media_by_id_and_serves_file | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_product_build_media_src_uses_token_for_absolute_local_... | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads | woo_media_route_uses_basename_for_local_file | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads | woo_media_route_serves_existing_absolute_local_file | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads | woo_media_route_detects_real_mime_from_file_content | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads | wc_orders_service_creates_missing_products_before_push | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads | wc_orders_service_push_order_updates_remote_order_and_log... | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads | customer_payload_and_repo_match_woo_customer_id | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads.customers | customer_payload_and_repo_match_woo_customer_id | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads.media | wc_product_build_media_src_uses_internal_public_host_when... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.media | wc_product_build_media_src_uses_token_for_absolute_local_... | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads.media | woo_media_route_resolves_media_by_id_and_serves_file | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.media | woo_media_route_uses_basename_for_local_file | ✅ PASSED | 0.002 |
| tests.db_objects.woo_payloads.media | woo_media_route_serves_existing_absolute_local_file | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.media | woo_media_route_detects_real_mime_from_file_content | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.orders | order_line_payload_uses_wc_tax_class_and_variation_id | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.orders | order_line_payload_raises_clear_error_when_product_not_sy... | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.orders | order_payload_uses_wc_customer_and_line_contract | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_uses_customer_woo_email_and_remote_cust... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_creates_missing_remote_customer_when_lo... | ✅ PASSED | 0.003 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_syncs_line_ids_from_wc_payload | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_creates_missing_products_before_push | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.orders | wc_orders_service_push_order_updates_remote_order_and_log... | ✅ PASSED | 0.005 |
| tests.db_objects.woo_payloads.products | general_object_payload_uses_wc_tax_slug | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | object_tag_payload_uses_wc_tag_id | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads.products | wc_product_payload_includes_synced_tags | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | update_product_syncs_missing_wc_tags_before_export | ✅ PASSED | 0.006 |
| tests.db_objects.woo_payloads.products | book_payload_keeps_woo_attribute_keys | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads.products | other_object_payload_has_empty_attributes | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads.products | variation_payload_uses_wc_keys | ✅ PASSED | 0.000 |
| tests.db_objects.woo_payloads.products | wc_diff_objects_detects_create_update_and_delete_batches | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | wc_product_builds_catalog_payload_with_merged_attributes | ✅ PASSED | 0.001 |
| tests.db_objects.woo_payloads.products | wc_product_update_fails_when_woo_returns_no_wc_id | ✅ PASSED | 0.004 |
| tests.db_objects.woo_payloads.products | match_line_to_wc_uses_product_and_variation_ids | ✅ PASSED | 0.001 |

---

*Generated on 2026-08-18 17:15:54*
