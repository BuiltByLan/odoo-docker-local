from odoo import models, fields, api, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    platform_price = fields.Float(
        string='Platform Price', default=1.0)
    platform_sub_total = fields.Float(
        compute='_compute_amount_platform', store=True,)
    
    
    @api.depends('platform_price', 'product_uom_qty')
    def _compute_amount_platform(self):
        for line in self:
            line.platform_sub_total = line.platform_price * line.product_uom_qty