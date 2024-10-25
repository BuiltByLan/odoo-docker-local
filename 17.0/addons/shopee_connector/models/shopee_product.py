import requests
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
import hmac
import hashlib

_logger = logging.getLogger(__name__)


class ProductEcommerce(models.Model):
    _inherit = 'product.ecommerce'

    product_shopee_id = fields.Char('Shopee ID', tracking=True, readonly=True, index=True)

    # @api.constrains('product_id')
    # def _check_product_shopee_id(self):
    #     for record in self:
    #         if record.product_id:
    #             product = self.env['product.ecommerce'].search([
    #                 ('platform', '=', 'shopee'),
    #                 ('product_id', '=', record.product_id.id), 
    #                 ('id', '!=', record.id)], limit=1)
    #             if product:
    #                 raise UserError('Product already mapped to another Shopee product')
    
    @staticmethod
    def get_timestamp():
        current_datetime = datetime.now()
        return int(current_datetime.timestamp())
    
    def get_product_shopee_list_data(self, offset, page_size):
        base_url = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.url_shopee', '')
        token_shopee = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.token_shopee', '')
        partner_id = int(self.env['ir.config_parameter'].sudo().get_param('shopee_connector.partner_id_shopee', 0))
        shop_id = int(self.env['ir.config_parameter'].sudo().get_param('shopee_connector.shopee_shop_id', ''))
        partner_key_shopee = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.partner_key_shopee', False)
        path = "/api/v2/product/get_item_list"
        url = f"{base_url}{path}"
        time_s = self.get_timestamp()
        partner_key = partner_key_shopee.encode()
        tmp_base_string = "%s%s%s%s%s" % (partner_id, path, time_s, token_shopee, shop_id)
        base_string = tmp_base_string.encode()

        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
        headers = {}
        payload={}
        params = {
            'access_token': token_shopee,
            'timestamp': self.get_timestamp(),
            'offset': offset,
            'page_size': page_size,
            'item_status': 'NORMAL',
            'partner_id': partner_id,
            'sign': sign,
            'shop_id': shop_id,
        }
        
        response = requests.get(url, headers=headers,data=payload, params=params, allow_redirects=False, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', {})
        else:
            _logger.error(response.text)

    def get_item_base_info(self, item_ids):
        base_url = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.url_shopee', '')
        token_shopee = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.token_shopee', '')
        partner_id = int(self.env['ir.config_parameter'].sudo().get_param('shopee_connector.partner_id_shopee', 0))
        shop_id = int(self.env['ir.config_parameter'].sudo().get_param('shopee_connector.shopee_shop_id', ''))
        partner_key_shopee = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.partner_key_shopee', False)
        path = "/api/v2/product/get_item_base_info"
        url = f"{base_url}{path}"
        headers = {}
        payload = {}
        
        partner_key = partner_key_shopee.encode()
        tmp_base_string = "%s%s%s%s%s" % (partner_id, path, self.get_timestamp(), token_shopee, shop_id)
        base_string = tmp_base_string.encode()
        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()

        params = {
            'access_token': token_shopee,
            'timestamp': self.get_timestamp(),
            'partner_id': partner_id,
            'shop_id': shop_id,
            'sign': sign,
            'item_id_list': item_ids,
        }
        
        response = requests.get(url, headers=headers, data=payload, params=params, allow_redirects=False, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', {})
        else:
            return {}

    def _create_product_shopee(self, datas):
        product_vals = []
        product_ecommerce_model = self.env['product.ecommerce'].sudo()
        
        for product in datas:
            item_id = product.get('item_id', '')
            item_sku = product.get('item_sku', '')
            shopee_product_id = product_ecommerce_model.search([
                ('product_shopee_id', '=', item_id)], limit=1)
            
            if not shopee_product_id:
                product_product = self.env['product.product'].sudo().search([
                    ('default_code', '=',item_sku)], limit=1)
                
                tmp_product_check = product_ecommerce_model.search([
                    ('product_id', '=', product_product.id)], limit=1)
                
                product_val = {
                'name': product.get("item_name", ""),
                'product_shopee_id': item_id,
                'price': product.get("price_info", [])[0].get('current_price', 0),
                'quantity': product.get('stock_info_v2', {}).get('seller_stock', [])[0].get('stock', 0) if not product.get('stock_info', []) else product.get('stock_info', [])[0].get('normal_stock', 0),
                'sku': item_sku,
                'platform': 'shopee',
                }
                if product_product and not tmp_product_check:
                    product_val['product_id'] = product_product.id
            
                product_vals.append(product_val)
            
        if product_vals:
            product_ecommerce_model.create(product_vals)

    def save_product_shopee_list_data(self):
        try:
            offset = 0
            page_size = 50
            while True:
                result = self.get_product_shopee_list_data(offset, page_size)
                data_list_item = result.get('item', [])
                has_next_page = result.get('has_next_page', False) 
                item_list = []
                for data in data_list_item:
                    item_id = data.get('item_id', 0)
                    item_list.append(item_id)
                items_base_info = self.get_item_base_info(item_list)
                datas = items_base_info.get('item_list', []) 
                self._create_product_shopee(datas)
                if not has_next_page:
                    break
                else:
                    offset += page_size

        except Exception as e:
            _logger.error(e)
            
        return {
            'name': _("Products"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.ecommerce',
            'view_mode': 'tree',
            'domain': [('platform', '=', 'shopee')],
            'views': [(False, 'tree')],
        }
