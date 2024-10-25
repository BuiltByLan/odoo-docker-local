from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_shopee_id = fields.Char('Partner Shopee ID', index=True)

    def _cron_fix_partner_platform_shopee(self):
        partners = self.search([('partner_shopee_id', '!=', False)])
        for partner in partners:
            partner.ecommerce_platform = 'shopee'
