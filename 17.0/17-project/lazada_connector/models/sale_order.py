from odoo import fields, models, _
from odoo.exceptions import UserError

from collections import Counter
from datetime import datetime
from ..lazop.base import LazopClient, LazopRequest

import logging
import requests
import base64
import json

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lazada_order_id = fields.Char(string="Lazada Order ID", readonly=False, index=True)
    lazada_status=fields.Char(string="Order Status", readonly=False, tracking=True)
    lazada_status_update_time = fields.Datetime(string="Update Time", readonly=False, tracking=True)
    lazada_package_id = fields.Char(string="Lazada Package ID")
    lazada_tracking_number = fields.Char("Lazada Tracking Number")
    lazada_document_url = fields.Char("URL lazada document")
    
    def check_partner_laz_id(self, buyer_id, email, name, phone_number, street):
        """
        Check if a partner with the given Lazada ID exists. If not, create one.
    
        Args:
            buyer_id (str): Lazada buyer ID.
            email (str): Email of the buyer.
            name (str): Name of the buyer.
            phone_number (str): Phone number of the buyer.
            street (str): Street address of the buyer.
    
        Returns:
            int: ID of the partner.
        """
        partner_model = self.env['res.partner']
        partner = partner_model.search([('partner_lazada_id', '=', str(buyer_id))], limit=1)
        
        if not partner:
            partner = partner_model.create({
                'name': name,
                'email': email,
                'mobile': phone_number,
                'type': 'contact',
                'street': street,
                'partner_lazada_id': buyer_id,
                'ecommerce_platform': 'lazada',
            })
        
        return partner.id
    
    def check_order_lazada_exist(self, order_id):
        order = self.env['sale.order'].search([('lazada_order_id', '=', order_id)], limit=1)
        if order:
            return order
        return False

    def change_order_status_in_laz(self, order, status, date):
        """
        #! unpaid, topack
        #? pending
        #! ready_to_ship
        #! delivered, shipped
        #! toship, shipping, 
        #* failed, , lost
        #* returned, canceled
        """
        order.write({
            'lazada_status_update_time': date
        })
        if status in ["unpaid", "topack", "pending"]:
            return True
        elif status in ["ready_to_ship"]:
            order.action_confirm()
        elif status in ["toship", "shipping"]:
            order.action_in_transit()
        elif status in [ "shipped"]:
            order.action_delivered()
        elif status == "delivered":
            order.action_completed()    
        else: # status == "canceled"
            order.action_cancel()
            
    def process_order_status_lazada(self, order_data, lines_data):
        """
        Process the order status from Lazada and update or create the order in Odoo.
        """
        order = self.check_order_lazada_exist(order_data.get('order_id'))
        _logger.info("SO LAZADA: %s", order)

        statuses = order_data.get('statuses')[0]
        if not order:
            product_counter = Counter([x.get('product_id') for x in lines_data])
            for line in lines_data:
                line["count_product"] = product_counter[line["product_id"]]

            prepared_line_items = self._prepare_line_items(lines_data)
            customer_id = self._get_customer_id(order_data, lines_data)

            if prepared_line_items:
                pre_data = self._prepare_order_data(order_data, customer_id, prepared_line_items)
                order_lazada = self.env['sale.order'].create(pre_data)
                _logger.info("SO NEW LAZADA: %s", order_lazada)
                order_lazada.change_order_status_in_laz(order_lazada, statuses, datetime.strptime(order_data.get('created_at')[:19], '%Y-%m-%d %H:%M:%S'))
        else:
            _logger.info("SO LAZADA UPDATE: %s %s", order, statuses)
            if order_data.get('statuses')[0] == 'ready_to_ship':
                package_id = lines_data[0].get('package_id')
                if package_id:
                    order.write({
                        'lazada_package_id': package_id,
                        'lazada_status': statuses
                    })
            else:
                order.sudo().write({'lazada_status': statuses})
            order.change_order_status_in_laz(order, statuses, datetime.strptime(order_data.get('updated_at')[:19], '%Y-%m-%d %H:%M:%S'))

    def _prepare_line_items(self, lines_data):
        """
        Prepare line items for the order.
        """
        def filter_line_items(lines_data):
            product_ids = {}
            for item in lines_data:
                product_id = item['product_id']
                if product_id not in product_ids:
                    product_ids[product_id] = item
            return list(product_ids.values())

        prepared_line_items = []
        pricelist = self.pricelist_id if self.pricelist_id else \
            self.env['ir.config_parameter'].sudo().get_param('lazada_connector.pricelist_id')
        for line in filter_line_items(lines_data):
            lazada_product_id = self.env['product.ecommerce'].sudo().search([
                ('product_lazada_id', '=', line.get('product_id', ''))], limit=1)
            if not lazada_product_id:
                continue
            product = lazada_product_id.product_id
            prepared_line_items.append({
                'product_id': product.id,
                'product_uom_qty': line.get('count_product', 1),
                'price_unit': product.list_price if not pricelist else \
                    self.pricelist_id._get_product_price(product, line.get('count_product', 1)),
                'platform_price': line.get('item_price', 0) - line.get('voucher_seller', 0),
                'tax_id': [(6, 0, [])],
            })
        return prepared_line_items

    def _get_customer_id(self, order_data, lines_data):
        """
        Get or create the customer ID based on the order data.
        """
        line_item = lines_data[0]
        customer_name = order_data.get('address_shipping').get('first_name') + order_data.get('address_shipping').get('last_name')
        customer_id = self.check_partner_laz_id(
            line_item.get('buyer_id'),
            order_data.get('address_shipping').get('email'),
            customer_name,
            order_data.get('address_shipping').get('phone2'),
            order_data.get('address_shipping').get('address1'))
        return customer_id

    def _prepare_order_data(self, order_data, customer_id, prepared_line_items):
        """
        Prepare the order data for creating a new order.
        """
        return {
            'name': order_data.get('order_number', ''),
            'lazada_order_id': order_data.get('order_id'),
            'partner_id': customer_id,
            'note': order_data.get('remarks', ''),
            'order_line': [(0, 0, line) for line in prepared_line_items],
            'ecommerce_platform': 'lazada',
            'lazada_status': order_data.get('statuses')[0],
            'create_time_platform': datetime.strptime(order_data.get('created_at')[:19], '%Y-%m-%d %H:%M:%S')
        }
        
    def common_params(self):
        config_param = self.env['ir.config_parameter'].sudo()
        access_token = config_param.get_param('lazada_connector.access_token')
        appkey = config_param.get_param('lazada_connector.app_key_lazada')
        appSecret = config_param.get_param('lazada_connector.app_secret_lazada')
        url = config_param.get_param('lazada_connector.api_service_lazada')
        
        return access_token, appkey, appSecret, url
    
    def print_awb_package_document(self, package_id):
        """
        Args:
            order (str): The order ID.
        Returns:
            dict: The response data containing awb package document.
        """
        _logger.info('AWB Package Document Package: %s', package_id)
        access_token, appkey, appSecret, url = self.common_params()
        path = '/order/package/document/get'
        client = LazopClient(url, appkey ,appSecret)
        request = LazopRequest(path)
        response = client.execute(request, access_token)
        
        json_string = json.dumps({
            "doc_type": "PDF",
            "packages": [{"package_id": package_id}]
        })
        # {"doc_type":"PDF","packages":[{"package_id":"FP092111266863628"}]}
        request.add_api_param('getDocumentReq', json_string)
        response = client.execute(request, access_token)
        return response.body

    def write(self, vals):
        if 'lazada_package_id' in vals and vals['lazada_package_id']:
            package = vals['lazada_package_id']
            try:
                _logger.info('Downloading PDF Lazada %s', self.lazada_order_id)
                body = self.print_awb_package_document(package)
                if body.get('code') == '0':
                    url = body.get('result').get('data').get('pdf_url')
                    response = requests.get(url)
                    response.raise_for_status()
                    pdf_content = response.content

                    attachment = self.env['ir.attachment'].create({
                        'name': 'lazada_shipping_label_%s.pdf' % self.lazada_order_id,
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'sale.order',
                        'res_id': self.id,
                        'mimetype': 'application/pdf',
                    })
                    self.tracking_document_id = attachment.id
                    _logger.info('PDF attachment created: %s', self.lazada_order_id)
                else:
                    return super(SaleOrder, self).write(vals)

            except requests.exceptions.RequestException as e:
                _logger.error('Failed to download PDF: %s', e)
        return super(SaleOrder, self).write(vals)
    
    def test_call_document_lazada(self, package_id):
        body = self.print_awb_package_document(package_id)
        if body.get('code') == '0':
            url = body.get('result').get('data').get('pdf_url')
            response = requests.get(url)
            response.raise_for_status()
            pdf_content = response.content

            attachment = self.env['ir.attachment'].create({
                'name': 'test_lazada_%s.pdf' % package_id,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'sale.order',
                'mimetype': 'application/pdf',
            })