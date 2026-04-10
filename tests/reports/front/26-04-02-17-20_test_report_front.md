# Rapport des Tests - pytest tests

**Date:** 2026-04-02T17:20:07.252472
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
| tests.front.admin | index | ✅ PASSED | 0.095 |
| tests.front.admin | create_first_user | ✅ PASSED | 0.069 |
| tests.front.customer | permissions[client_all-200-routes0-<!DOCTYPE html>\n<html... | ✅ PASSED | 0.169 |
| tests.front.customer | permissions[client-302-routes1-<!doctype html>\n<html lan... | ✅ PASSED | 0.017 |
| tests.front.customer | permissions[client_informatique-403-routes2-<!DOCTYPE htm... | ✅ PASSED | 0.043 |
| tests.front.customer | permissions[client_compta-200-routes3-<!DOCTYPE html>\n<h... | ✅ PASSED | 0.081 |
| tests.front.customer | permissions[client_commercial-200-routes4-<!DOCTYPE html>... | ✅ PASSED | 0.077 |
| tests.front.customer | permissions[client_direction-200-routes5-<!DOCTYPE html>\... | ✅ PASSED | 0.078 |
| tests.front.customer | search_fast_pro_part[tes-1-pro-complete_customer_pro] | ✅ PASSED | 0.010 |
| tests.front.customer | search_fast_pro_part[jan-1-part-complete_customer_part] | ✅ PASSED | 0.010 |
| tests.front.customer | search_fast_pro_part[xyz-0-None-None] | ✅ PASSED | 0.006 |
| tests.front.customer | search_fast_pro_part[-0-None-None] | ✅ PASSED | 0.002 |
| tests.front.dashboard | dashboard_authorization[routes0-client-302] | ✅ PASSED | 0.003 |
| tests.front.dashboard | dashboard_authorization[routes1-client_informatique-403] | ✅ PASSED | 0.008 |
| tests.front.dashboard | dashboard_authorization[routes2-client_compta-200] | ✅ PASSED | 0.005 |
| tests.front.dashboard | dashboard_authorization[routes3-client_commercial-200] | ✅ PASSED | 0.004 |
| tests.front.dashboard | dashboard_authorization[routes4-client_direction-200] | ✅ PASSED | 0.005 |
| tests.front.dashboard | dashboard_authorization[routes5-client_admin-200] | ✅ PASSED | 0.004 |
| tests.front.dashboard | dashboard_authorization[routes6-client_logistique-200] | ✅ PASSED | 0.004 |
| tests.front.inventory | inventory_authorization_denied[route0-client-302] | ✅ PASSED | 0.020 |
| tests.front.inventory | inventory_authorization_denied[route1-client_informatique... | ✅ PASSED | 0.025 |
| tests.front.inventory | inventory_authorization_success[client_direction] | ✅ PASSED | 0.061 |
| tests.front.inventory | inventory_authorization_success[client_logistique] | ✅ PASSED | 0.034 |
| tests.front.inventory | inventory_authorization_success[client_support] | ✅ PASSED | 0.033 |
| tests.front.inventory | inventory_authorization_success[client_admin] | ✅ PASSED | 0.034 |
| tests.front.inventory_e2e.TestInventoryE2E | workflow_single_product | ✅ PASSED | 0.018 |
| tests.front.inventory_e2e.TestInventoryE2E | workflow_with_unknown_product | ✅ PASSED | 0.029 |
| tests.front.inventory_e2e.TestInventoryE2E | workflow_with_existing_stock | ✅ PASSED | 0.019 |
| tests.front.order | order_index_access[client_direction] | ✅ PASSED | 0.004 |
| tests.front.order | order_index_access[client_logistique] | ✅ PASSED | 0.004 |
| tests.front.order | order_index_access[client_support] | ✅ PASSED | 0.004 |
| tests.front.order | order_index_access[client_admin] | ✅ PASSED | 0.004 |
| tests.front.stocks | cleared_authenticated | ✅ PASSED | 0.002 |
| tests.front.stocks | cleared_unauthenticated | ✅ PASSED | 0.001 |
| tests.front.stocks | search_table | ✅ PASSED | 0.030 |
| tests.front.stocks | dilicom_modal | ✅ PASSED | 0.011 |
| tests.front.stocks | object_autocomplete | ✅ PASSED | 0.009 |
| tests.front.stocks | create_tag_htmx | ✅ PASSED | 0.006 |
| tests.front.stocks | object_form | ✅ PASSED | 0.018 |
| tests.front.stocks | object_view_or_edit | ✅ PASSED | 0.016 |
| tests.front.stocks | object_complement | ✅ PASSED | 0.032 |
| tests.front.stocks | create_object | ✅ PASSED | 0.016 |
| tests.front.stocks | edit_object | ✅ PASSED | 0.011 |
| tests.front.stocks | object_toggle_active_modal | ✅ PASSED | 0.011 |
| tests.front.stocks | object_toggle_active | ✅ PASSED | 0.014 |
| tests.front.stocks | dilicom_add | ✅ PASSED | 0.018 |
| tests.front.stocks | dilicom_remove | ✅ PASSED | 0.013 |
| tests.front.stocks | index | ✅ PASSED | 0.011 |
| tests.front.stocks | council | ✅ PASSED | 0.012 |
| tests.front.stocks | orders | ✅ PASSED | 0.021 |
| tests.front.stocks | create_order | ✅ PASSED | 0.010 |
| tests.front.stocks | create_return | ✅ PASSED | 0.003 |
| tests.front.stocks | search | ✅ PASSED | 0.006 |
| tests.front.stocks | cleared_return | ✅ PASSED | 0.002 |
| tests.front.stocks | returns | ✅ PASSED | 0.009 |
| tests.front.stocks | new_return_section | ✅ PASSED | 0.005 |
| tests.front.stocks | view_return | ✅ PASSED | 0.010 |
| tests.front.stocks | new_return_table | ✅ PASSED | 0.004 |
| tests.front.stocks | new_return_line_form | ✅ PASSED | 0.003 |
| tests.front.stocks | cleared_orders | ✅ PASSED | 0.002 |
| tests.front.stocks | orders_htmx | ✅ PASSED | 0.006 |
| tests.front.stocks | new_order_section | ✅ PASSED | 0.033 |
| tests.front.stocks | edit_order | ✅ PASSED | 0.011 |
| tests.front.stocks | view_order | ✅ PASSED | 0.011 |
| tests.front.stocks | cancel_order | ✅ PASSED | 0.020 |
| tests.front.stocks | new_order_line | ✅ PASSED | 0.017 |
| tests.front.stocks | edit_order_line | ✅ PASSED | 0.019 |
| tests.front.stocks | confirm_order | ✅ PASSED | 0.017 |
| tests.front.stocks | receipt_order | ✅ PASSED | 0.012 |
| tests.front.stocks | receive_order_line | ✅ PASSED | 0.023 |
| tests.front.stocks | update_external_ref | ✅ PASSED | 0.013 |
| tests.front.stocks | api_update_price | ✅ PASSED | 0.014 |
| tests.front.stocks | api_create_order | ✅ PASSED | 0.007 |
| tests.front.supplier | index | ✅ PASSED | 0.008 |
| tests.front.supplier | get_suppliers | ✅ PASSED | 0.014 |
| tests.front.supplier | add_new_supplier | ✅ PASSED | 0.005 |
| tests.front.supplier | create_supplier_htmx | ✅ PASSED | 0.006 |
| tests.front.supplier | select_supplier | ✅ PASSED | 0.004 |
| tests.front.supplier | select_dilicom_supplier | ✅ PASSED | 0.003 |
| tests.front.supplier | close_modal | ✅ PASSED | 0.002 |
| tests.front.user | login | ✅ PASSED | 1.516 |
| tests.front.user | register | ✅ PASSED | 0.011 |
| tests.front.user | logout | ✅ PASSED | 0.012 |
| tests.front.user | chg_pwd | ✅ PASSED | 0.866 |
| tests.front.user | modify | ✅ PASSED | 0.038 |

---

*Generated on 2026-04-02 17:20:07*
