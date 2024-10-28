{
    'name': 'Shopee Connector',
    'version': '1.1',
    'description': '',
    'author': 'thaidt',
    'license': 'LGPL-3',
    'category': 'Extra Tools',
    'depends': ['ecommerce_sale'],
    'data': [
        "security/ir.model.access.csv",
        "views/res_config_setting_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/shopee_product_views.xml",
        "views/shopee_message_views.xml",
        "data/ir_cron.xml",
        ],
    'auto_install': False,
    'application': False,
}