import re
from odoo import fields, _, models, api
from odoo.exceptions import UserError
from collections import defaultdict


REGEX_PHONE = "^(?:0)\d{9}$"


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ["res.partner", "address.mixin"]
    
    transporter_type = fields.Selection(
        selection=[('internal', 'Internal'), ('external', 'External')],
        string='Transporter Type',
    )
    transporter_code = fields.Char(
        string='Transporter Code',
    )
    is_transporter = fields.Boolean(
        string='Transporter',
        readonly=True,
    )