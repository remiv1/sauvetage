# Rapport des Tests - pytest tests

**Date:** 2026-08-22T15:13:15.427251+02:00
**Suite:** pytest tests

---

## Summary

| Metric | Value |
| ------ | ----- |
| **Status** | ✅ ALL TESTS PASSED |
| **Total Tests** | 115 |
| **Passed** | ✅ 115 |
| **Failed** | ❌ 0 |
| **Skipped** | ⊘ 0 |
| **Pass Rate** | 100.0% |

---

## Detailed Results

| Test Class | Test Name | Status | Time (s) |
| ---------- | --------- | ------ | -------- |
| tests.front.admin | index | ✅ PASSED | 3.152 |
| tests.front.admin | create_first_user | ✅ PASSED | 0.069 |
| tests.front.customer | permissions[client_all-200-routes0-<!DOCTYPE html>\n<html... | ✅ PASSED | 0.756 |
| tests.front.customer | permissions[client-302-routes1-<!doctype html>\n<html lan... | ✅ PASSED | 0.063 |
| tests.front.customer | permissions[client_informatique-403-routes2-<!DOCTYPE htm... | ✅ PASSED | 0.611 |
| tests.front.customer | permissions[client_compta-200-routes3-<!DOCTYPE html>\n<h... | ✅ PASSED | 0.463 |
| tests.front.customer | permissions[client_commercial-200-routes4-<!DOCTYPE html>... | ✅ PASSED | 0.468 |
| tests.front.customer | permissions[client_direction-200-routes5-<!DOCTYPE html>\... | ✅ PASSED | 0.465 |
| tests.front.customer | search_fast_pro_part[tes-1-pro-complete_customer_pro] | ✅ PASSED | 0.043 |
| tests.front.customer | search_fast_pro_part[jan-1-part-complete_customer_part] | ✅ PASSED | 0.041 |
| tests.front.customer | search_fast_pro_part[xyz-0-None-None] | ✅ PASSED | 0.027 |
| tests.front.customer | search_fast_pro_part[-0-None-None] | ✅ PASSED | 0.022 |
| tests.front.dashboard | dashboard_authorization[routes0-client-302] | ✅ PASSED | 0.010 |
| tests.front.dashboard | dashboard_authorization[routes1-client_informatique-403] | ✅ PASSED | 0.093 |
| tests.front.dashboard | dashboard_authorization[routes2-client_compta-200] | ✅ PASSED | 0.111 |
| tests.front.dashboard | dashboard_authorization[routes3-client_commercial-200] | ✅ PASSED | 0.057 |
| tests.front.dashboard | dashboard_authorization[routes4-client_direction-200] | ✅ PASSED | 0.056 |
| tests.front.dashboard | dashboard_authorization[routes5-client_admin-200] | ✅ PASSED | 0.058 |
| tests.front.dashboard | dashboard_authorization[routes6-client_logistique-200] | ✅ PASSED | 0.056 |
| tests.front.dashboard | dashboard_finances_retourne_les_series_mensuelles | ✅ PASSED | 0.013 |
| tests.front.dashboard | dashboard_stock_by_category_retourne_les_totaux | ✅ PASSED | 0.016 |
| tests.front.dashboard | dashboard_stock_slow_moving_limite_et_trie_les_articles | ✅ PASSED | 0.017 |
| tests.front.dashboard | dashboard_commandes_rejette_une_pagination_invalide[pagin... | ✅ PASSED | 0.013 |
| tests.front.dashboard | dashboard_commandes_rejette_une_pagination_invalide[pagin... | ✅ PASSED | 0.012 |
| tests.front.inventory | inventory_authorization_denied[route0-client-302] | ✅ PASSED | 0.066 |
| tests.front.inventory | inventory_authorization_denied[route1-client_informatique... | ✅ PASSED | 0.328 |
| tests.front.inventory | inventory_authorization_success[client_direction] | ✅ PASSED | 0.308 |
| tests.front.inventory | inventory_authorization_success[client_logistique] | ✅ PASSED | 0.197 |
| tests.front.inventory | inventory_authorization_success[client_support] | ✅ PASSED | 0.197 |
| tests.front.inventory | inventory_authorization_success[client_admin] | ✅ PASSED | 0.197 |
| tests.front.inventory_e2e.TestInventoryE2E | workflow_single_product | ✅ PASSED | 0.079 |
| tests.front.inventory_e2e.TestInventoryE2E | workflow_with_unknown_product | ✅ PASSED | 0.114 |
| tests.front.inventory_e2e.TestInventoryE2E | workflow_with_existing_stock | ✅ PASSED | 0.086 |
| tests.front.order | order_index_access[client_direction] | ✅ PASSED | 0.052 |
| tests.front.order | order_index_access[client_logistique] | ✅ PASSED | 0.042 |
| tests.front.order | order_index_access[client_support] | ✅ PASSED | 0.043 |
| tests.front.order | order_index_access[client_admin] | ✅ PASSED | 0.043 |
| tests.front.order | order_article_search_accepts_ean13_or_title | ✅ PASSED | 0.088 |
| tests.front.stocks | cleared_authenticated | ✅ PASSED | 0.021 |
| tests.front.stocks | create_reservation_with_context | ✅ PASSED | 0.133 |
| tests.front.stocks | cleared_unauthenticated | ✅ PASSED | 0.005 |
| tests.front.stocks | search_table | ✅ PASSED | 0.107 |
| tests.front.stocks | dilicom_modal | ✅ PASSED | 0.045 |
| tests.front.stocks | supplier_object_filter_for_order_line | ✅ PASSED | 0.160 |
| tests.front.stocks | supplier_object_search_uses_exact_ean13 | ✅ PASSED | 0.072 |
| tests.front.stocks | supplier_object_search_keeps_supplier_filter_for_ean13 | ✅ PASSED | 0.038 |
| tests.front.stocks | order_object_dropdown_does_not_limit_quantity_like_reserv... | ✅ PASSED | 0.039 |
| tests.front.stocks | object_autocomplete | ✅ PASSED | 0.046 |
| tests.front.stocks | create_tag_htmx | ✅ PASSED | 0.034 |
| tests.front.stocks | object_form | ✅ PASSED | 0.096 |
| tests.front.stocks | object_view_or_edit | ✅ PASSED | 0.073 |
| tests.front.stocks | object_complement | ✅ PASSED | 0.143 |
| tests.front.stocks | create_object | ✅ PASSED | 0.084 |
| tests.front.stocks | create_object_with_variations | ✅ PASSED | 0.060 |
| tests.front.stocks | create_object_without_variation | ✅ PASSED | 0.045 |
| tests.front.stocks | edit_object_add_variation | ✅ PASSED | 0.080 |
| tests.front.stocks | edit_object | ✅ PASSED | 0.053 |
| tests.front.stocks | object_toggle_active_modal | ✅ PASSED | 0.049 |
| tests.front.stocks | object_toggle_active | ✅ PASSED | 0.054 |
| tests.front.stocks | dilicom_add | ✅ PASSED | 0.063 |
| tests.front.stocks | dilicom_remove | ✅ PASSED | 0.053 |
| tests.front.stocks | index | ✅ PASSED | 0.064 |
| tests.front.stocks | council | ✅ PASSED | 0.062 |
| tests.front.stocks | orders | ✅ PASSED | 0.101 |
| tests.front.stocks | create_order | ✅ PASSED | 0.064 |
| tests.front.stocks | create_return | ✅ PASSED | 0.038 |
| tests.front.stocks | search | ✅ PASSED | 0.048 |
| tests.front.stocks | cleared_return | ✅ PASSED | 0.022 |
| tests.front.stocks | returns | ✅ PASSED | 0.045 |
| tests.front.stocks | new_return_section | ✅ PASSED | 0.041 |
| tests.front.stocks | view_return | ✅ PASSED | 0.055 |
| tests.front.stocks | new_return_table | ✅ PASSED | 0.037 |
| tests.front.stocks | new_return_line_form | ✅ PASSED | 0.039 |
| tests.front.stocks | cleared_orders | ✅ PASSED | 0.023 |
| tests.front.stocks | orders_htmx | ✅ PASSED | 0.037 |
| tests.front.stocks | new_order_section | ✅ PASSED | 0.072 |
| tests.front.stocks | edit_order | ✅ PASSED | 0.051 |
| tests.front.stocks | view_order | ✅ PASSED | 0.045 |
| tests.front.stocks | cancel_order | ✅ PASSED | 0.083 |
| tests.front.stocks | create_reservation_line | ✅ PASSED | 0.081 |
| tests.front.stocks | delete_reservation_line_reintegrates_stock | ✅ PASSED | 0.026 |
| tests.front.stocks | new_order_line | ✅ PASSED | 0.091 |
| tests.front.stocks | edit_order_line | ✅ PASSED | 0.073 |
| tests.front.stocks | confirm_order | ✅ PASSED | 0.066 |
| tests.front.stocks | confirm_order_mail_choice | ✅ PASSED | 0.050 |
| tests.front.stocks | send_order_mail_success_and_failure_states | ✅ PASSED | 0.061 |
| tests.front.stocks | receipt_order | ✅ PASSED | 0.044 |
| tests.front.stocks | receive_order_line | ✅ PASSED | 0.075 |
| tests.front.stocks | update_external_ref | ✅ PASSED | 0.048 |
| tests.front.stocks | api_update_price | ✅ PASSED | 0.086 |
| tests.front.stocks | api_create_order | ✅ PASSED | 0.039 |
| tests.front.supplier | index | ✅ PASSED | 0.048 |
| tests.front.supplier | get_suppliers | ✅ PASSED | 0.078 |
| tests.front.supplier | add_new_supplier | ✅ PASSED | 0.052 |
| tests.front.supplier | create_supplier_htmx | ✅ PASSED | 0.040 |
| tests.front.supplier | select_supplier | ✅ PASSED | 0.029 |
| tests.front.supplier | select_dilicom_supplier | ✅ PASSED | 0.025 |
| tests.front.supplier | close_modal | ✅ PASSED | 0.022 |
| tests.front.user | login | ✅ PASSED | 2.216 |
| tests.front.user | register | ✅ PASSED | 0.130 |
| tests.front.user | logout | ✅ PASSED | 0.105 |
| tests.front.user | logout_revokes_server_session | ✅ PASSED | 0.059 |
| tests.front.user | revoked_session_redirects_on_next_protected_request | ✅ PASSED | 0.031 |
| tests.front.user | disabled_or_locked_account_invalidates_existing_session[i... | ✅ PASSED | 0.313 |
| tests.front.user | disabled_or_locked_account_invalidates_existing_session[i... | ✅ PASSED | 0.321 |
| tests.front.user | permissions_are_refreshed_before_authorization | ✅ PASSED | 0.048 |
| tests.front.user | expired_or_idle_session_is_rejected[expires_at] | ✅ PASSED | 0.310 |
| tests.front.user | expired_or_idle_session_is_rejected[last_seen_at] | ✅ PASSED | 0.316 |
| tests.front.user | authentication_backend_failure_returns_service_unavailable | ✅ PASSED | 0.035 |
| tests.front.user | login_creates_distinct_opaque_server_sessions | ✅ PASSED | 0.598 |
| tests.front.user | change_password_requires_authenticated_owner_or_administr... | ✅ PASSED | 0.400 |
| tests.front.user | administrator_roles_can_reset_another_users_password[1] | ✅ PASSED | 0.326 |
| tests.front.user | administrator_roles_can_reset_another_users_password[9] | ✅ PASSED | 0.314 |
| tests.front.user | password_change_revokes_server_sessions | ✅ PASSED | 1.194 |
| tests.front.user | modify | ✅ PASSED | 0.276 |

---

*Generated on 2026-08-22 15:13:35*
