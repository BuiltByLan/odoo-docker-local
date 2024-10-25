from odoo import api, fields, models

class WizardSortProductInventory(models.TransientModel):
    _name = 'wizard.sort.product.inventory'
    _description = 'Wizard to Sort Product Inventory by Date Range'

    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    platform = fields.Selection([
        ('tiktok', 'TikTok'),
        ('shopee', 'Shopee'),
        ('lazada', 'Lazada')
    ], string='Platform', required=True)
    picking_type = fields.Selection([
        ('PICK', 'PICK'),
        ('PACK', 'PACK'),
        ('OUT', 'OUT')
    ], string='Picking Type', required=True)

    def action_sort_inventory(self):
        self.ensure_one()
        sale_orders = self.env['sale.order'].search([
            ('create_time_platform', '>=', self.start_date),
            ('create_time_platform', '<', self.end_date),
            ('ecommerce_platform', '=', self.platform),
            ('state', '=', 'sale')
        ])
        
        picking_ids = sale_orders.mapped('picking_ids').filtered(
            lambda r: r.state != 'done' and r.picking_type_id.sequence_code == self.picking_type
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sorted Inventory',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', picking_ids.ids)],
            'context': {'create': False},
        }