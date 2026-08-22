# Rapport des Tests - pytest tests

**Date:** 2026-08-22T15:13:39.019096+02:00
**Suite:** pytest tests

---

## Summary

| Metric | Value |
| ------ | ----- |
| **Status** | ✅ ALL TESTS PASSED |
| **Total Tests** | 38 |
| **Passed** | ✅ 38 |
| **Failed** | ❌ 0 |
| **Skipped** | ⊘ 0 |
| **Pass Rate** | 100.0% |

---

## Detailed Results

| Test Class | Test Name | Status | Time (s) |
| ---------- | --------- | ------ | -------- |
| tests.back.dilicom_import | price_ht_uses_taxable_amount_when_present | ✅ PASSED | 0.127 |
| tests.back.dilicom_import | reproduces_dif499492052_price_year_and_metadata | ✅ PASSED | 0.158 |
| tests.back.dilicom_import | dilicom_real_file_extracts_language_collection_dimensions... | ✅ PASSED | 0.038 |
| tests.back.dilicom_import | dilicom_extracts_bnf_metadata_when_present | ✅ PASSED | 0.020 |
| tests.back.dilicom_import | get_values_from_onix_returns_sqlalchemy_object_price | ✅ PASSED | 0.020 |
| tests.back.dilicom_import | save_or_update_from_object_keeps_taxable_amount_and_vat_r... | ✅ PASSED | 0.370 |
| tests.back.dilicom_import | dilicom_service_uses_cached_vat_rates | ✅ PASSED | 0.015 |
| tests.back.dilicom_import | update_status_handles_already_created_reference | ✅ PASSED | 0.014 |
| tests.back.dilicom_import | save_or_update_from_object_is_idempotent_on_same_ean | ✅ PASSED | 0.037 |
| tests.back.documents_api | create_document_logs_exception_and_raises_500 | ✅ PASSED | 0.002 |
| tests.back.mails_api | send_mail_payload_returns_smtp_acceptance | ✅ PASSED | 0.007 |
| tests.back.mails_api | send_mail_payload_rejects_invalid_base64_attachment | ✅ PASSED | 0.001 |
| tests.back.mails_api | send_mail_payload_returns_502_on_smtp_error | ✅ PASSED | 0.004 |
| tests.back.mails_api | build_supplier_order_mail_returns_500_when_pdf_generation... | ✅ PASSED | 0.004 |
| tests.back.mails_api | build_supplier_order_mail_uses_company_config_and_order_date | ✅ PASSED | 0.004 |
| tests.back.mails_api | send_supplier_order_mail_returns_404_when_order_is_missing | ✅ PASSED | 0.001 |
| tests.back.security_migration_decorators | get_security_token_requires_configured_token | ✅ PASSED | 0.002 |
| tests.back.security_migration_decorators | get_security_token_returns_configured_token | ✅ PASSED | 0.001 |
| tests.back.security_migration_decorators | build_dsn_encodes_migration_credentials | ✅ PASSED | 0.001 |
| tests.back.security_migration_decorators | run_alembic_returns_subprocess_result | ✅ PASSED | 0.002 |
| tests.back.security_migration_decorators | run_alembic_handles_subprocess_error | ✅ PASSED | 0.002 |
| tests.back.security_migration_decorators | run_startup_tasks_migrates_when_lock_is_obtained | ✅ PASSED | 0.008 |
| tests.back.security_migration_decorators | run_startup_tasks_falls_back_when_postgres_lock_fails | ✅ PASSED | 0.083 |
| tests.back.security_migration_decorators | ensure_vat_adds_only_missing_rates | ✅ PASSED | 0.004 |
| tests.back.security_migration_decorators | access_control_validates_token_and_ip | ✅ PASSED | 0.001 |
| tests.back.security_migration_decorators | access_control_rejects_invalid_requests[internal_request0... | ✅ PASSED | 0.001 |
| tests.back.security_migration_decorators | access_control_rejects_invalid_requests[internal_request1... | ✅ PASSED | 0.001 |
| tests.back.security_migration_decorators | access_control_rejects_invalid_requests[internal_request2... | ✅ PASSED | 0.001 |
| tests.back.sync_partners | sync_customer_pushes_to_both_partners | ✅ PASSED | 0.003 |
| tests.back.sync_partners | sync_customer_isolates_partner_failures | ✅ PASSED | 0.004 |
| tests.back.sync_partners | sync_customer_logs_update_operation_for_known_partners | ✅ PASSED | 0.003 |
| tests.back.sync_partners | sync_customer_logs_henrri_validation_details | ✅ PASSED | 0.004 |
| tests.back.sync_partners | sync_all_products_exports_woocommerce_then_henrri | ✅ PASSED | 0.003 |
| tests.back.sync_partners | sync_all_products_reports_woocommerce_failure_without_blo... | ✅ PASSED | 0.005 |
| tests.back.vat_sync | new_vat_rate_closes_superseded_rate_at_its_effective_time | ✅ PASSED | 0.009 |
| tests.back.vat_sync | vat_slug_duplicates_are_rejected_before_woocommerce_sync | ✅ PASSED | 0.004 |
| tests.back.vat_sync | vat_sync_is_skipped_when_woocommerce_already_matches | ✅ PASSED | 0.004 |
| tests.back.vat_sync | vat_slug_change_triggers_woocommerce_resynchronization | ✅ PASSED | 0.005 |

---

*Generated on 2026-08-22 15:13:43*
