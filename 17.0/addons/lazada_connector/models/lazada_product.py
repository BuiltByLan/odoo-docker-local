from odoo import fields, models, api, _
from odoo.exceptions import UserError

from ..lazop.base import LazopClient, LazopRequest
import logging
_logger = logging.getLogger(__name__)

class ProductEcommerce(models.Model):
    _inherit = 'product.ecommerce'
    
    lzd_seller_sku = fields.Char('Seller SKU', tracking=True)
    product_lazada_id = fields.Char('ID', tracking=True, readonly=True)
    warehouse_lazada_id = fields.Char('Warehouse ID', tracking=True, readonly=True)
    
    def get_product_lazada_platform(self):
        try:
            access_token = self.env['ir.config_parameter'].sudo().get_param('lazada_connector.access_token')
            appkey = self.env['ir.config_parameter'].sudo().get_param('lazada_connector.app_key_lazada')
            appSecret = self.env['ir.config_parameter'].sudo().get_param('lazada_connector.app_secret_lazada')
            url = self.env['ir.config_parameter'].sudo().get_param('lazada_connector.api_service_lazada')
            offset = 0
            limit = 50
            
            client = LazopClient(url, appkey ,appSecret)
            
            while True:
                request = LazopRequest('/products/get','GET')
                request.add_api_param('filter', 'live')
                request.add_api_param('offset', str(offset))
                request.add_api_param('limit', str(limit))
                request.add_api_param('options', '0')
                response = client.execute(request, access_token)
                res_data = response.body.get('data', {})
                if not res_data:
                    break
                else:
                    if res_data.get('products'):
                        product_vals = []
                        for product in response.body['data']['products']:
                            # status=product.get("status", "")
                            product_id = self.env['product.ecommerce'].sudo().search([
                                ('platform', '=', 'lazada'),
                                ('product_lazada_id', '=', product.get("item_id", ""))], limit=1)
                            if not product_id:
                                product_vals.append({
                                    'name': product.get("attributes", {}).get("name", ""),
                                    'product_lazada_id': product.get("item_id", ""),
                                    'price': product.get("skus", [{}])[0].get("price", ""),
                                    'quantity': product.get("skus", [{}])[0].get("quantity", ""),
                                    'sku': product.get("skus", [{}])[0].get("SkuId", ""),
                                    'lzd_seller_sku': product.get("skus", [{}])[0].get("SellerSku", ""),
                                    'warehouse_lazada_id': product.get("skus", [{}])[0].get("ShopSku", ""),
                                    'platform': 'lazada',
                                })
                            else:
                                product_id.write({
                                    'sku': product.get("skus", [{}])[0].get("SkuId", ""),
                                    'price': product.get("skus", [{}])[0].get("price", ""),
                                    'quantity': product.get("skus", [{}])[0].get("quantity", ""),
                                    'warehouse_lazada_id': product.get("skus", [{}])[0].get("ShopSku", ""),
                                })
                        if product_vals:
                            self.env['product.ecommerce'].sudo().create(product_vals)
                
                offset += limit
        
        except Exception as e:
            _logger.info(str(e))

        return {
            'name': _("Products"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.ecommerce',
            'view_mode': 'tree',
            'domain': [('platform', '=', 'lazada')],
            'views': [(False, 'tree')],
        }     