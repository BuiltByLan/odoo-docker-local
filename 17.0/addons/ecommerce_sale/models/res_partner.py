from odoo import models, fields, api

class Partner(models.Model):
    _inherit = 'res.partner'

    is_ecommerce = fields.Boolean(
        string='Is Ecommerce Customer',
        help='Check this box if the customer is created from the ecommerce website.', readonly=True
    )
    ecommerce_platform = fields.Selection([
            ('tiktok', 'TikTok'),
            ('shopee', 'Shopee'),
            ('lazada', 'Lazada'),
            ('other', 'Other'),
        ],string="Platform", readonly=True)
    
    @api.model
    def create(self, vals):
        # Override the create method to set the is_ecommerce field
        # based on the context key 'is_ecommerce'
        if self._context.get('is_ecommerce'):
            vals.update({'is_ecommerce': True})
        return super(Partner, self).create(vals)
    
    def write(self, vals):
        # Override the write method to set the is_ecommerce field
        # based on the context key 'is_ecommerce'
        if self._context.get('is_ecommerce'):
            vals.update({'is_ecommerce': True})
        return super(Partner, self).write(vals)
    
    def action_view_sale_orders(self):
        action = self.env.ref('sale.action_orders').read()[0]
        action['domain'] = [('partner_id', '=', self.id)]
        return action