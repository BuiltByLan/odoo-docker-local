from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_tiktok_id = fields.Char('Partner Tiktok ID', index=True)

    def _cron_platform_partner_tiktok(self):
        partners = self.search([('partner_tiktok_id', '!=', False)])
        for partner in partners:
            partner.ecommerce_platform = 'tiktok'