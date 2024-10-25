from odoo import fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


import logging

_logger = logging.getLogger(__name__)

class TransportOrder(models.Model):

    _inherit = 'transport.order'
    
    