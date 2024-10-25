from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
import requests
import urllib.request
import urllib.parse
from .sign_api_request import cal_sign, get_timestamp, get_cipher_shop_key

_logger = logging.getLogger(__name__)

class ProductEcommerce(models.Model):
    _inherit = 'product.ecommerce'

    product_tiktok_id = fields.Char('TikTok ID', tracking=True, readonly=True)
    warehouse_tiktok_id = fields.Char('Warehouse ID', tracking=True, readonly=True)
    tiktok_currency = fields.Char(string="Currency" ,tracking=True, readonly=True)
    
    # @api.constrains('product_id')
    # def _check_product_tiktok_id(self):
    #     for record in self:
    #         if record.product_id and record.platform == 'tiktok':
    #             product = self.env['product.ecommerce'].search([
    #                 ('product_id', '=', record.product_id.id), 
    #                 ('id', '!=', record.id)], limit=1)
    #             if product:
    #                 raise UserError('Product already mapped to another TikTok product')

    def get_product_list_data(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.url_tiktok', '')
        token = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.token_tiktok', '')
        app_key = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_key_tiktok', '')
        app_secret = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_secret_tiktok', '')
        
        path = "/product/202309/products/search"
        url = f"{base_url}{path}"
        headers = {
             "Content-Type": "application/json",
             "x-tts-access-token": f"{token}",
        }
        shop_cipher = get_cipher_shop_key(app_key, app_secret, token, base_url)
        params = {
            # "access_token": token,
            "app_key": app_key,
            "page_size": 100,
            "shop_cipher": shop_cipher.get("data").get("shops")[0].get("cipher"),
            "timestamp": get_timestamp(),
            "version": "202309",
        }

        params_signed = urllib.parse.urlencode(params)
        url_signed = f"{url}?{params_signed}"
        params['sign'] = cal_sign(url_signed, app_secret)
        
        response = requests.post(url, headers=headers, params=params, verify=False, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    def save_product_list_tiktok_data(self):
        try:
            datas = self.get_product_list_data().get('data', {}).get('products', [])
            if not datas:
                pass
            else:
                product_vals = []
                for product in datas:
                    product_id = self.env['product.ecommerce'].sudo().search([
                        ('platform', '=', 'tiktok'),
                        ('product_tiktok_id', '=', product.get('id', ''))], limit=1)
                    sku = product.get("skus", [{}])[0]
                    if not product_id:
                        product_vals.append({
                            'name': product.get("title", ""),
                            'product_tiktok_id': product.get("id", ""),
                            'price': sku.get("price", {}).get("tax_exclusive_price", ""),
                            'quantity': sku.get("inventory", [{}])[0].get("quantity", ""),
                            'sku': sku.get('id', ''),
                            'tiktok_currency': sku.get("price", {}).get("currency", ""),
                            'warehouse_tiktok_id': sku.get("inventory", [{}])[0].get("warehouse_id", ''),
                            'platform': 'tiktok',
                        })
                    else:
                        product_id.write({
                            'sku': sku.get('id', ''),
                            'price': sku.get("price", {}).get("tax_exclusive_price", ""),
                            'quantity': sku.get("inventory", [{}])[0].get("quantity", ""),
                            'warehouse_tiktok_id': sku.get("inventory", [{}])[0].get("warehouse_id", '')
                        })
                if product_vals:
                    self.env['product.ecommerce'].sudo().create(product_vals)
        except Exception as e:
            _logger.error(e)

        return {
            'name': _("Products"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.ecommerce',
            'view_mode': 'tree',
            'domain': [('platform', '=', 'tiktok')],
            'views': [(False, 'tree')],
        }
