from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

READONLY_STATES = {
    'sale': [('readonly', True)],
    'done': [('readonly', True)],
    'cancel': [('readonly', True)]
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    cod = fields.Monetary(
        string="COD",
        states=READONLY_STATES,
        tracking=True,
        copy=False,
    )
    shipping_method_id = fields.Many2one(
        'delivery.carrier',
        string='Shipping Method',
        ondelete='restrict',
        states=READONLY_STATES,
        domain="[('transporter_id', '=', transporter_id)]"
    )
    pay_fee_type = fields.Selection(
        string='Fee Paid By',
        selection=[
            ('customer', 'Customer pays delivery fee'),
            ('seller', 'Seller pays delivery fee'),
            ('other', 'Other pays delivery fee'),
        ],
        default='customer',
        states=READONLY_STATES,
    )
    transport_order_ids = fields.One2many(
        'transport.order',
        'sale_id',
        string='Transport Order',
        readonly=False,
        copy=False,
    )
    transporter_type = fields.Selection(
        string='Transporter Type',
        related='transporter_id.transporter_type',
    )
    amount_transporter = fields.Monetary(
        compute='_compute_amount_transporter',
        string='Amount Transporter',
        store=True,
    )
    
    @api.onchange('transporter_id')
    def _onchange_transporter_id(self):
        carrier_id = self.env['delivery.carrier'].search([
            ('transporter_id', '=', self.transporter_id.id)], limit=1)
        if carrier_id:
            self.shipping_method_id = carrier_id.id
        else:
            self.shipping_method_id = False
        self.sender_address_id = False

    def _prepare_transport_order(self):
        picking_ids = self.picking_ids.filtered(lambda r: r.state != 'cancel')
        vals = {
            "transporter_id": self.transporter_id.id,
            "sale_id": self.id,
            "picking_out_id": picking_ids and picking_ids[0].id or False,
            "cod": self.cod,
            "shipping_method_id": self.shipping_method_id.id,
            "pay_fee_type": self.pay_fee_type,
        }
        return vals

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for record in self:
            transport_orders = record.transport_order_ids.filtered(
                lambda r: r.state != 'cancel')
            if record.state == 'sale' and not transport_orders \
                    and record.transporter_id.transporter_type == 'internal' \
                    and record.transporter_id.transporter_code:
                vals = record._prepare_transport_order()
                self.env['transport.order'].create(vals)
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        self.transport_order_ids.action_cancel()
        return res

    @api.onchange('transporter_type')
    def _onchange_transporter_type(self):
        if self.transporter_type == 'external':
            self.pay_fee_type = 'customer'
        else:
            self.pay_fee_type = 'seller'

    def _prepare_delivery_api_log(self, transpoter_id, request, response, is_success):
        vals = {
            "transporter_id": transpoter_id.id,
            "request": request,
            "response": response,
            "is_success": is_success,
        }
        return vals

    @api.model
    def create(self, vals):
        if self._context.get('import_file', False):
            if 'transport_order_ids' in vals \
                    and not self.env.user.has_group("base.group_system"):
                vals.pop('transport_order_ids')
        return super(SaleOrder, self).create(vals)
    

    @api.depends(
        "cod",
        "company_id",
        "amount_total",
        # "order_line.invoice_lines.move_id",
        # "order_line.invoice_lines.move_id.amount_total",
    )
    def _compute_amount_transporter(self):
        
        pass