# -*- coding: utf-8 -*-
{
    "name": "Ecommerce Core",
    "version": "17.0.0.1",
    "author":  "thaidt",
    "category": "Extra Tools",
    "depends": [
        "base",
        "mail",
        "contacts",
        "delivery",
        "payment",
        "product",
        "sale",
        "sale_management",
        "sale_stock",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/res_partner_views.xml",
        "views/product_ecommerce_views.xml",
        "wizard/wizard_sort_product_inventory_view.xml",
        ],
    "installable": True,
    "application": False,
    "auto_install": False,
}