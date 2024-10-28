from odoo import models, fields, api
from odoo import tools
from datetime import datetime, timedelta
import pytz
from odoo.exceptions import ValidationError


class ShippingDocument(models.Model):
    _name = 'shipping.document'
    _description = 'Shipping Document'

    shipping_num_auto = fields.Char(string='Shipping Number', readonly=True)
    destination = fields.Char(string='Destination')
    shipping_cost = fields.Float(string='Shipping Cost')
    ecommerce_platform = fields.Selection([
        ('tiktok', 'Tiktok'),
        ('shopee', 'Shopee'),
        ('lazada', 'Lazada'),
        ], string='Ecommerce Platform')
    detail_ids = fields.One2many(
        'shipping.document.detail', 'shipping_document_id', string='Shipping Document Detail')
    state = fields.Selection([
        ('draft','Draft'),
        ('comfirmed','Confirmed'),
        ('return','Return')], default='draft', string="Status")
    
    
    def action_confirm(self):
        pass

    def action_cancel(self):
        pass

    def unlink(self):
        for record in self:
            if record.state in ['confirm', 'return']:
                raise ValidationError('Cannot delete approved or settled records!')
        return super().unlink()

    def name_get(self):
        result = []
        for record in self:
            rec_name = "%s" % (record.shipping_num_auto)
            result.append((record.id, rec_name))
        return result
       

class ShippingDocumentDetail(models.Model):
    _name = 'shipping.document.detail'
    _description = 'Shipping Document Detail'


    create_date=fields.Datetime()
    shipping_document_id = fields.Many2one('shipping.document', string='Shipping Document',ondelete='cascade')
