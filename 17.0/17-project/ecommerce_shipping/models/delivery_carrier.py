import psycopg2
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'
    
    transporter_id = fields.Many2one(
        string='Transporter',
        comodel_name='res.partner',
        ondelete='restrict',
        domain="[('is_transporter', '=', True)]"
    )
    service_code = fields.Char(
        string='Service Code',
    )
    product_id = fields.Many2one(
        required=False,
    )