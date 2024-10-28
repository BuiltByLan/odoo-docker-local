from odoo import models, fields, api
import requests


class ReturnOrder(models.Model):
    _name = 'tiktok.return.order'
    _description = 'TikTok Return Order'

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    tiktok_order_id = fields.Char(string='TikTok Order ID', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Integer(string='Quantity', required=True)
    reason = fields.Text(string='Return Reason')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tiktok.return.order') or _('New')
        result = super(ReturnOrder, self).create(vals)
        return result
    
    def action_awaiting_buyer_ship(self):
        self.write({'state': 'awaiting_buyer_ship'})

    def action_buyer_shipped_item(self):
        self.write({'state': 'buyer_shipped_item'})

    def action_receive_rejected(self):
        self.write({'state': 'receive_rejected'})

    def action_request_success(self):
        self.write({'state': 'request_success'})

    def action_request_complete(self):
        self.write({'state': 'return_or_refund_request_complete'})

    def action_request_rejected(self):
        self.write({'state': 'request_rejected'})

    def action_request_cancelled(self):
        self.write({'state': 'return_or_refund_cancel'})
   
   
     
class RefundOrder(models.Model):
    _name = 'tiktok.refund.order'
    _description = 'TikTok Refund Order'

    name = fields.Char(string='Refund Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    tiktok_order_id = fields.Char(string='TikTok Order ID', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Integer(string='Quantity', required=True)
    refund_amount = fields.Float(string='Refund Amount', required=True)
    reason = fields.Text(string='Refund Reason')
    state = fields.Selection([
        ('pending', 'RETURN_OR_REFUND_REQUEST_PENDING'),
        ('success', 'REQUEST_SUCCESS'),
        ('complete', 'RETURN_OR_REFUND_REQUEST_COMPLETE'),
        ('rejected', 'REQUEST_REJECTED'),
        ('cancelled', 'RETURN_OR_REFUND_CANCEL')
    ], string='Status', readonly=True, copy=False, index=True, default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tiktok.refund.order') or _('New')
        result = super(RefundOrder, self).create(vals)
        return result

    def action_request_success(self):
        self.write({'state': 'success'})

    def action_request_complete(self):
        self.write({'state': 'complete'})

    def action_request_rejected(self):
        self.write({'state': 'rejected'})

    def action_request_cancelled(self):
        self.write({'state': 'cancelled'})



class CancellationSearch:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url

    def search_cancellations(self, order_id=None, customer_id=None, status=None):
        params = {
            'order_id': order_id,
            'customer_id': customer_id,
            'status': status
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        path = '/return_refund/202309/cancellations/search'
        response = requests.get(f'{self.base_url}{path}', params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()