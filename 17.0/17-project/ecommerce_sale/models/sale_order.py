from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_ecommerce = fields.Boolean(
        string='Is Ecommerce Sale',
        help='Check this box if the sale order is created from the ecommerce website.'
    )
    ecommerce_platform = fields.Selection([
            ('tiktok', 'TikTok'),
            ('shopee', 'Shopee'),
            ('lazada', 'Lazada'),
            ('other', 'Other'),
        ],string="Platform",)

    state = fields.Selection(
        selection_add=[
            ('awaiting_shipment', 'Awaiting Shipment'),
            ('in_transit', 'In Transit'),
            ('delivered', 'Delivered'),
            ('completed', 'Completed'),
        ]
    )
    create_time_platform = fields.Datetime('Create Time', readonly=False,
        help='The time when the order was created in the ecommerce platform')
    price_platform_totals = fields.Monetary('Total Platform Price', 
        compute='_compute_price_platform_totals',
        store=True,
        help='The total price of the order in the ecommerce platform')
    
    tracking_document_id = fields.Many2one('ir.attachment', string='Tracking Document')
   
    @api.depends_context('lang') 
    @api.depends('order_line.platform_price', 'currency_id')
    def _compute_price_platform_totals(self):
        for order in self:
            order.price_platform_totals = sum(order.order_line.mapped('platform_sub_total'))

    #! draft -> awaiting_shipment (to_ship/to_process) -> awaiting_collection (to_ship processed) = done -> 
    #! in_transit (shipped) -> delivered (received) -> completed
    def action_awainting_shipment(self):
        self.write({'state': 'awaiting_shipment'})
        
    def action_in_transit(self):
        self.write({'state': 'in_transit'})
        
    def action_delivered(self):
        self.write({'state': 'delivered'})
        
    def action_completed(self):
        self.write({'state': 'completed'})