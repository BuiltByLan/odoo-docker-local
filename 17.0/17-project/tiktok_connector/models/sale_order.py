from odoo import fields, models, _
from odoo.exceptions import UserError
from datetime import datetime

from collections import Counter

import logging
import requests
import base64

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):

    _inherit = 'sale.order'
    
    tiktok_order_id = fields.Char('TikTok Order ID', readonly=False, index=True)
    tiktok_status = fields.Char('status', readonly=False, tracking=True)
    tiktok_update_time = fields.Datetime('Update Time', readonly=False, tracking=True)
    package_id = fields.Char('Tiktok Package ID')
    package_url = fields.Char('Tiktok Package URL')
    tiktok_tracking_number = fields.Char('Tiktok Tracking Number')
    
    def check_partner_tiktok_id(self, user_id, email, name, phone_number, street):
        """
        Check if a partner with the given TikTok user ID exists, and if not, create a new partner.
        Args:
            user_id (str): The TikTok user ID of the partner.
            email (str): The email address of the partner.
            name (str): The name of the partner.
            phone_number (str): The phone number of the partner.
            street (str): The street address of the partner.
        Returns:
            int: The ID of the existing or newly created partner.
        """
        
        partner_env = self.env['res.partner']
        partner = partner_env.search([('partner_tiktok_id', '=', user_id)], limit=1)
        if not partner:
            partner = partner_env.sudo().create({
                'type': 'contact', 
                'name': name,
                'email': email,
                'mobile': phone_number,
                'street': street,
                'partner_tiktok_id': user_id,
                'ecommerce_platform': 'tiktok',
            })
        return partner.id
    
    def check_order_tiktok_exist(self, order_id):
        order = self.env['sale.order'].search([('tiktok_order_id', '=', order_id)], limit=1)
        if order:
            return order
        return False
    
    def change_sale_order_status(self, order, status, date):
        order.write({
            'tiktok_update_time': datetime.fromtimestamp(date),
        })
        if status in ["UNPAID", "AWAITING_SHIPMENT"]:
            return True
        elif status == "AWAITING_COLLECTION":
            order.action_confirm()
        # elif status == "IN_TRANSIT":
        #     order.action_in_transit()
        elif status == "DELIVERED":
            order.action_delivered()
        elif status == "COMPLETED":
            order.action_completed()
        else: # status == "CANCELLED"
            order.action_cancel()
    
    def process_order_status_tiktok(self, data):
        """
        Processes the order status from TikTok and creates or updates the corresponding sale order in Odoo.
        Args:
            data (dict): A dictionary containing the order data from TikTok. Expected keys include:
                - 'id': The TikTok order ID.
                - 'status': The status of the order.
                - 'user_id': The user ID of the buyer.
                - 'buyer_email': The email of the buyer.
                - 'recipient_address': A dictionary containing the recipient's address details:
                    - 'name': The name of the recipient.
                    - 'phone_number': The phone number of the recipient.
                    - 'address_detail': The detailed address of the recipient.
                - 'packages': A list of packages associated with the order.
                - 'line_items': A list of line items in the order, each containing:
                    - 'product_id': The ID of the product.
                    - 'product_name': The name of the product.
                    - 'price': The price of the product.
                    - 'sku': The SKU of the product.
                    - 'count_product': The quantity of the product.
                    - 'sale_price': The sale price of the product.
                - 'buyer_message': A message from the buyer.
                - 'create_time': The creation time of the order (timestamp).
                - 'update_time': The last update time of the order (timestamp).
        Returns:
            None
        """
        
        order = self.check_order_tiktok_exist(data.get('id'))
        status = data.get('status','')
        if not order:
            customer_id = self.check_partner_tiktok_id(
                data.get('user_id',''),
                data.get('buyer_email', ''), 
                data.get('recipient_address',[]).get('name', ''),
                data.get('recipient_address',[]).get('phone_number', ''), 
                data.get('recipient_address',[]).get('address_detail', ''))
            
            packages = data.get('packages', [])
            package_id = packages[0].get('id', '') if packages else ''
            line_items = data.get("line_items", [])
            product_counter = Counter([x.get('product_id') for x in line_items])
            for line in line_items:
                line["count_product"] = product_counter[line["product_id"]]
                
            def filter_line_items(line_items):
                product_ids = {}
                for item in line_items:
                    product_id = item['product_id']
                    if product_id not in product_ids:
                        product_ids[product_id] = item
                return list(product_ids.values())
            
            prepared_line_items = []
            product_ecommerce = self.env['product.ecommerce'] 
            pricelist =  self.pricelist_id if self.pricelist_id else \
                self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.pricelist_id')
            for line in filter_line_items(line_items):
                tiktok_product_id = product_ecommerce.sudo().search([
                    ('platform', '=', 'tiktok'),
                    ('product_tiktok_id', '=', line.get('product_id', ''))], limit=1)
                if not tiktok_product_id:
                    product_tmp = self.env['product.product'].sudo().create({
                        'name': line.get('product_name', ''),
                        'list_price': line.get('price', ''),
                        'default_code': line.get('sku', ''),
                        'type': 'product',
                    })
                    vals = {
                        'name': line.get('product_name', ''),
                        'price': line.get('price', ''),
                        'sku': line.get('sku', ''),
                        'quantity': line.get('count_product', ''),
                        'platform': 'tiktok',
                        'product_tiktok_id': line.get('product_id', ''),
                        'product_id': product_tmp.id,
                    }
                    tiktok_product_id = product_ecommerce.create(vals)
                    
                prepared_line_items.append({
                    'product_id': tiktok_product_id.product_id.id,
                    'product_uom_qty': line.get('count_product', 1),
                    'price_unit': tiktok_product_id.product_id.list_price if not pricelist else \
                        self.pricelist_id._get_product_price(tiktok_product_id.product_id, line.get('count_product', 1)),
                    'platform_price': line.get('sale_price', ''),
                    'tax_id': [(6, 0, [])],
                })
            if prepared_line_items:
                pre_data={
                    'name': data.get('id', ''),
                    'tiktok_order_id': data.get('id', ''),
                    'partner_id': customer_id,
                    'note': data.get('buyer_message', ''),
                    'order_line': [(0, 0, line) for line in prepared_line_items],
                    'ecommerce_platform': 'tiktok',
                    'tiktok_status': status,
                    'create_time_platform': datetime.fromtimestamp(data.get('create_time', 0)),
                    'package_id': package_id,
                }
            order_tiktok = self.env['sale.order'].create(pre_data)
            order_tiktok.change_sale_order_status(order_tiktok, status, data.get('update_time', ''))

    def write(self, vals):
        """
        Overrides the write method to handle the downloading and attaching of a PDF 
        from a given URL when the 'package_url' field is present in the vals dictionary.
        Args:
            vals (dict): Dictionary of field values to be written to the record.
        Returns:
            bool: True if the write operation was successful, otherwise False.
        Raises:
            requests.exceptions.RequestException: If there is an error while downloading the PDF.
        Side Effects:
            - Downloads a PDF from the provided 'package_url'.
            - Creates an attachment record for the downloaded PDF.
            - Sets the 'tracking_document_id' field to the ID of the created attachment.
        """
        
        if 'package_url' in vals and vals['package_url']:
            url = vals['package_url']
            tiktok_id = self.tiktok_order_id
            try:
                _logger.info('Downloading PDF for %s', tiktok_id)
                response = requests.get(url)
                response.raise_for_status()
                pdf_content = response.content

                attachment = self.env['ir.attachment'].create({
                    'name': 'tiktok_shipping_label_%s.pdf' % tiktok_id,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'sale.order',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                self.tracking_document_id = attachment.id
                _logger.info('PDF attachment created: %s', tiktok_id)
            except requests.exceptions.RequestException as e:
                _logger.error('Failed to download PDF: %s', e)
        return super(SaleOrder, self).write(vals)
    
    #TODO LATER   
    def get_tracking_info(self):
        method = "GET"
        path = '/fulfillment/202309/orders/{order_id}/tracking'
        # {
        #     "code": 0,
        #     "data": {
        #         "tracking": [
        #         {
        #             "description": "Your package has been delivered.",
        #             "update_time_millis": 1723173772419
        #         },
        #         {
        #             "description": "Your package has been collected by our carrier.",
        #             "update_time_millis": 1723172791988
        #         },
        #         {
        #             "description": "The seller is preparing your package, and will hand it over to our carrier for shipping.",
        #             "update_time_millis": 1723100996046
        #         }
        #         ]
        #     },
        #     "message": "Success",
        #     "request_id": "202408130409090BDBBF2281C1A268CBD0"
        # }
        pass
    

    def test_get_shipping_label(self, order_id):
        order = self.env['sale.order'].browse(order_id)
        url = order.package_url
        tiktok_id = order.tiktok_order_id
        try:
            _logger.info('Downloading PDF for %s', tiktok_id)
            response = requests.get(url)
            response.raise_for_status()
            pdf_content = response.content

            attachment = self.env['ir.attachment'].create({
                'name': 'tiktok_shipping_label_%s.pdf' % tiktok_id,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'sale.order',
                'res_id': self.id,
                'mimetype': 'application/pdf',
            })
            self.tracking_document_id = attachment.id
            _logger.info('PDF attachment created: %s', tiktok_id)
        except requests.exceptions.RequestException as e:
            _logger.error('Failed to download PDF: %s', e)