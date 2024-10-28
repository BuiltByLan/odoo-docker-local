from odoo import models, fields


class TiktokMessage(models.Model):
    _name = 'tiktok.message'
    _description = 'Tiktok Message'
    _order = 'create_date desc'
    
    name = fields.Char(string='Name')
    type_request = fields.Integer(string='Type Request')
    tts_notification_id = fields.Char(string='TTS Notification ID')
    shop_id = fields.Char(string='Shop ID')
    order_id = fields.Char(string='Order ID')
    tiktok_order_status = fields.Char(string='Tiktok Order Status')
    timestamp = fields.Char(string='Timestamp')
    data_raw = fields.Text(string='Data Raw')
    
# class TiktokTrackingMessage(models.Model):
#     _name = 'tiktok.tracking.message'
#     _description = 'Tiktok Tracking Message'
#     _order = 'create_date desc'
    
#     name = fields.Char(string='Name')
#     description = fields.Char(string='Description')
#     sale_order_id = fields.Many2one('sale.order', string='Sale Order')
#     tracking_number = fields.Char(string='Tracking Number')
    