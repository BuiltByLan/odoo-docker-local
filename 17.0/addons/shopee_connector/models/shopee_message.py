from odoo import models, fields


class ShopeeMessage(models.Model):
    _name = 'shopee.message'
    _description = 'Shopee Message'
    _order = 'create_date desc'
    
    name = fields.Char(string='Name')
    code_request = fields.Integer(string='Code')
    shop_id = fields.Char(string='Shop ID')
    timestamp = fields.Char(string='Timestamp')
    data_raw = fields.Text(string='Data Raw')
    order_sn = fields.Char(string='Order SN')
    status_order = fields.Char(string='Status Order')