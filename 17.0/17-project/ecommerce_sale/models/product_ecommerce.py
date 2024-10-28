from odoo import models, fields, api, _


class ProductEcommerce(models.Model):
    _name = 'product.ecommerce'
    _description = 'Product Ecommerce Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    
    
    name = fields.Char(string='Name', tracking=True)
    description = fields.Text(string='Description', tracking=True)
    price = fields.Float(string='Price', tracking=True)
    quantity = fields.Integer(string='Quantity', tracking=True)
    sku = fields.Char(string='SKU', tracking=True)
    platform = fields.Selection([
        ('tiktok', 'TikTok'),
        ('shopee', 'Shopee'),
        ('lazada', 'Lazada'),
        ('other', 'Other'),
    ], string='Platform')
    synced_price = fields.Boolean(string='Sync Price', tracking=True)
    synced_quantity = fields.Boolean(string='Sync Quantity', tracking=True)
    product_id = fields.Many2one('product.product', string='Product')

    