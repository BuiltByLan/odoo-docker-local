from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TransportOrder(models.Model):
    _name = 'transport.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Transport Order'
    _rec_name = 'name'
    _order = 'id DESC'

    name = fields.Char(
        string='Code',
        required=True,
        default=lambda self: ('New'),
        copy=False,
        readonly=True,
    )
    transporter_id = fields.Many2one(
        'res.partner', string='Transporter', 
        ondelete='restrict',
    )
    sale_id = fields.Many2one(
        'sale.order', string='Sale Order',
        ondelete='restrict',
        index=True,
    )
    picking_out_id = fields.Many2one(
        string='Picking Out',
        comodel_name='stock.picking',
        ondelete='restrict',
        index=True,
    )
    cod = fields.Monetary(
        string="COD",
        tracking=True,
    )
    shipping_method_id = fields.Many2one(
        string='Shipping Method',
        comodel_name='delivery.carrier',
        ondelete='restrict',
        domain="[('transporter_id', '=', transporter_id)]"
    )
    shipping_fee = fields.Monetary(
        string='Shipping Fee',
    )
    state = fields.Selection(
        string='Status',
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('cancel', 'Cancel'),
        ],
        required=True,
        tracking=True,
    )
    pay_fee_type = fields.Selection(
        string='Fee Paid By',
        selection=[
            ('customer', 'Customer pays delivery fee'),
            ('seller', 'Seller pays delivery fee'),
            ('other', 'Other pays delivery fee'),
        ],
        default='customer',
    )
    plan_picking_date = fields.Datetime(
        string='Plan Picking Date',
        default=fields.Datetime.now,
    )
    plan_shipping_date = fields.Datetime(
        string='Plan Shipping Date',
        default=fields.Datetime.now,
    )
    delivery_status = fields.Selection(
        selection=[
            ('delivered', 'Delivered'),
            ('returned', 'Returned'),
        ]
    )
    ecommerce_platform = fields.Selection(relate='sale_id.ecommerce_platform', string='Ecommerce Platform')
        

    @api.model
    def _get_transport_name(self):
        return self.env["ir.sequence"].next_by_code("transport.order.code")

    @api.model
    def create(self, vals):
        if vals.get('name') == "New" or not vals.get('name', False):
            vals['name'] = self._get_transport_name()
        return super(TransportOrder, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.constrains('sale_id', 'state')
    def _check_sale_id(self):
        for record in self:
            if record.sale_id:
                check_exist = self.search_count([
                    ('id', '!=', record.id),
                    ('sale_id', '=', record.sale_id.id),
                    ('state', 'in', ['unreconcile', 'reconcile']),
                ])
                if check_exist:
                    raise UserError(_("Order only allows to create one transport order."))

    def unlink(self):
        if self.filtered(lambda r: r.state != 'cancel'):
            raise UserError(_("You can only delete transport order in cancel state."))
        return super(TransportOrder, self).unlink()

    def _prepare_delivery_api_log(self, transpoter_id, request, response, is_success):
        vals = {
            "transporter_id": transpoter_id.id,
            "request": request,
            "response": response,
            "is_success": is_success,
        }
        return vals
