from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_lazada_id = fields.Char('Partner Lazada ID', index=True)
