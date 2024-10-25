import json

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError


class LazadaMessage(models.Model):
    _name = 'lazada.message'
    _description = 'Lazada Message'
    _order = 'create_date desc'
    
    name = fields.Char(string='Name')
    type_request = fields.Integer(string='Type Request')
    seller_id = fields.Char(string='Seller ID')
    timestamp = fields.Char(string='Timestamp')
    site_message = fields.Char(string='Site Message')
    data_raw = fields.Text(string='Data Raw')
    
    # {
        #     "seller_id":"1234567",  //seller Id
        #     "message_type":0,
        #     "data":{
        #         "order_status":"unpaid", //Order Status
        #         "trade_order_id":"260422900198363", //trade order Id
        #         "trade_order_line_id":"260422900298363", //sub order Id
        #         "status_update_time":1603698638 //update time (seconds)
        #     },
        #     "timestamp":1603766859530, //time when notify(seconds)
        #     "site":"lazada_vn" //site
    # }