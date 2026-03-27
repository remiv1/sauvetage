# Rapport des Tests - pytest tests

**Date:** 2026-03-27T11:23:54.795552
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
| front.admin | index | ✅ PASSED | 0.095 |
| front.admin | create_first_user | ✅ PASSED | 0.059 |
| front.customer | permissions[client_all-200-routes0-<!DOCTYPE html>\n<html... | ✅ PASSED | 0.157 |
| front.customer | permissions[client-302-routes1-<!doctype html>\n<html lan... | ✅ PASSED | 0.017 |
| front.customer | permissions[client_informatique-403-routes2-<!doctype htm... | ✅ PASSED | 0.022 |
| front.customer | permissions[client_compta-200-routes3-<!DOCTYPE html>\n<h... | ✅ PASSED | 0.080 |
| front.customer | permissions[client_commercial-200-routes4-<!DOCTYPE html>... | ✅ PASSED | 0.076 |
| front.customer | permissions[client_direction-200-routes5-<!DOCTYPE html>\... | ✅ PASSED | 0.078 |
| front.customer | search_fast_pro_part[tes-1-pro-complete_customer_pro] | ✅ PASSED | 0.010 |
| front.customer | search_fast_pro_part[jan-1-part-complete_customer_part] | ✅ PASSED | 0.010 |
| front.customer | search_fast_pro_part[xyz-0-None-None] | ✅ PASSED | 0.004 |
| front.customer | search_fast_pro_part[-0-None-None] | ✅ PASSED | 0.002 |
| front.dashboard | dashboard_authorization[routes0-client-302] | ✅ PASSED | 0.002 |
| front.dashboard | dashboard_authorization[routes1-client_informatique-403] | ✅ PASSED | 0.004 |
| front.dashboard | dashboard_authorization[routes2-client_compta-200] | ✅ PASSED | 0.005 |
| front.dashboard | dashboard_authorization[routes3-client_commercial-200] | ✅ PASSED | 0.004 |
| front.dashboard | dashboard_authorization[routes4-client_direction-200] | ✅ PASSED | 0.004 |
| front.dashboard | dashboard_authorization[routes5-client_admin-200] | ✅ PASSED | 0.005 |
| front.dashboard | dashboard_authorization[routes6-client_logistique-200] | ✅ PASSED | 0.004 |
| front.inventory | inventory_authorization_denied[route0-client-302] | ✅ PASSED | 0.019 |
| front.inventory | inventory_authorization_denied[route1-client_informatique... | ✅ PASSED | 0.014 |
| front.inventory | inventory_authorization_success[client_direction] | ✅ PASSED | 0.069 |
| front.inventory | inventory_authorization_success[client_logistique] | ✅ PASSED | 0.050 |
| front.inventory | inventory_authorization_success[client_support] | ✅ PASSED | 0.059 |
| front.inventory | inventory_authorization_success[client_admin] | ✅ PASSED | 0.040 |
| front.inventory_e2e.TestInventoryE2E | workflow_single_product | ✅ PASSED | 0.029 |
| front.inventory_e2e.TestInventoryE2E | workflow_with_unknown_product | ✅ PASSED | 0.030 |
| front.inventory_e2e.TestInventoryE2E | workflow_with_existing_stock | ✅ PASSED | 0.018 |
| front.order | order_index_access[client_direction] | ✅ PASSED | 0.003 |
| front.order | order_index_access[client_logistique] | ✅ PASSED | 0.004 |
| front.order | order_index_access[client_support] | ✅ PASSED | 0.004 |
| front.order | order_index_access[client_admin] | ✅ PASSED | 0.004 |
| front.stocks | cleared_authenticated | ✅ PASSED | 0.002 |
| front.stocks | cleared_unauthenticated | ✅ PASSED | 0.001 |
| front.stocks | search_table | ✅ PASSED | 0.026 |
| front.stocks | dilicom_modal | ✅ PASSED | 0.009 |
| front.stocks | object_autocomplete | ✅ PASSED | 0.010 |
| front.stocks | create_tag_htmx | ✅ PASSED | 0.005 |
| front.stocks | object_form | ✅ PASSED | 0.016 |
| front.stocks | object_view_or_edit | ✅ PASSED | 0.013 |
| front.stocks | object_complement | ✅ PASSED | 0.034 |
| front.stocks | create_object | ✅ PASSED | 0.015 |
| front.stocks | edit_object | ✅ PASSED | 0.010 |
| front.stocks | object_toggle_active_modal | ✅ PASSED | 0.009 |
| front.stocks | object_toggle_active | ✅ PASSED | 0.014 |
| front.stocks | dilicom_add | ✅ PASSED | 0.017 |
| front.stocks | dilicom_remove | ✅ PASSED | 0.013 |
| front.stocks | index | ✅ PASSED | 0.011 |
| front.stocks | council | ✅ PASSED | 0.009 |
| front.stocks | orders | ✅ PASSED | 0.015 |
| front.stocks | create_order | ✅ PASSED | 0.010 |
| front.stocks | create_return | ✅ PASSED | 0.003 |
| front.stocks | search | ✅ PASSED | 0.007 |
| front.stocks | cleared_return | ✅ PASSED | 0.002 |
| front.stocks | returns | ✅ PASSED | 0.007 |
| front.stocks | new_return_section | ✅ PASSED | 0.002 |
| front.stocks | view_return | ✅ PASSED | 0.009 |
| front.stocks | new_return_table | ✅ PASSED | 0.002 |
| front.stocks | new_return_line_form | ✅ PASSED | 0.002 |
| front.stocks | cleared_orders | ✅ PASSED | 0.002 |
| front.stocks | orders_htmx | ✅ PASSED | 0.007 |
| front.stocks | new_order_section | ✅ PASSED | 0.027 |
| front.stocks | edit_order | ✅ PASSED | 0.012 |
| front.stocks | view_order | ✅ PASSED | 0.010 |
| front.stocks | cancel_order | ✅ PASSED | 0.017 |
| front.stocks | new_order_line | ✅ PASSED | 0.015 |
| front.stocks | edit_order_line | ✅ PASSED | 0.019 |
| front.stocks | confirm_order | ✅ PASSED | 0.014 |
| front.stocks | receipt_order | ✅ PASSED | 0.010 |
| front.stocks | receive_order_line | ✅ PASSED | 0.018 |
| front.stocks | update_external_ref | ✅ PASSED | 0.012 |
| front.stocks | api_update_price | ✅ PASSED | 0.009 |
| front.stocks | api_create_order | ✅ PASSED | 0.005 |
| front.supplier | index | ✅ PASSED | 0.002 |
| front.supplier | get_suppliers | ✅ PASSED | 0.011 |
| front.supplier | add_new_supplier | ✅ PASSED | 0.005 |
| front.supplier | create_supplier_htmx | ✅ PASSED | 0.006 |
| front.supplier | select_supplier | ✅ PASSED | 0.004 |
| front.supplier | select_dilicom_supplier | ✅ PASSED | 0.004 |
| front.supplier | close_modal | ✅ PASSED | 0.002 |
| front.user | login | ✅ PASSED | 1.500 |
| front.user | register | ✅ PASSED | 0.008 |
| front.user | logout | ✅ PASSED | 0.011 |
| front.user | chg_pwd | ✅ PASSED | 0.856 |
| front.user | modify | ✅ PASSED | 0.034 |

---

*Generated on 2026-03-27 11:23:54*
