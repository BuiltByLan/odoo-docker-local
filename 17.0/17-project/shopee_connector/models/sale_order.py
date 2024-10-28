from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from bs4 import BeautifulSoup

import base64
import json
import requests
import hmac
import hashlib
import time
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopee_status = fields.Char('status', readonly=False)
    shopee_order_id = fields.Char('Shopee Order ID', readonly=False, index=True)
    shopee_update_time = fields.Datetime('Shopee Update Time', readonly=False)
    shopee_tracking_number = fields.Char('Shopee Tracking Number')
    shopee_package_number = fields.Char('Shopee Package Number')
    note_document = fields.Text(string='Description Document Shopee')
    
    def check_partner_shopee_id(self, partner_shopee_id, name, phone_number):
        """
        Checks if a partner with the given Shopee ID exists. If not, creates a new partner.
        Args:
            partner_shopee_id (str): The Shopee ID of the partner.
            name (str): The name of the partner.
            phone_number (str): The phone number of the partner.
        Returns:
            int: The ID of the existing or newly created partner.
        """
        
        partner = self.env['res.partner'].search([('partner_shopee_id', '=', 
                                                   partner_shopee_id)], limit=1)        
        if not partner:
            partner = self.env['res.partner'].create({
                'name': name,
                'mobile': phone_number,
                'type': 'contact',
                'ecommerce_platform': 'shopee',
                'partner_shopee_id': partner_shopee_id,
            })        
        return partner.id

    def check_order_shopee_exist(self, ordersn):
        """
        Check if a Shopee order exists in the system.
        This method searches for a sale order in the Odoo system using the provided Shopee order number (ordersn).
        If an order with the given Shopee order ID exists, it returns the order record. Otherwise, it returns False.
        Args:
            ordersn (str): The Shopee order number to search for.
        Returns:
            recordset or bool: The sale order record if found, otherwise False.
        """
        
        order_id = self.env['sale.order'].search([('shopee_order_id', '=', ordersn)], limit=1)
        if order_id:
            return order_id
        return False
    
    def _update_order_shopee(self, order_id, status, date):
        order_id.write({
            'shopee_update_time': date,
        })
        if status in ["UNPAID", "INVOICE_PENDING", "PROCESSED", "IN_CANCEL", "TO_CONFIRM_RECEIVE"]:
            return True
        elif status == "READY_TO_SHIP":
            order_id.action_confirm()
            
        #! ? check status in transit    
        # elif order['order_status'] == "":
        #     order.action_in_transit()
        elif status == "SHIPPED":
            order_id.action_delivered()
        elif status == "COMPLETED":
            order_id.action_completed()    
        elif status == "CANCELLED":
            order_id.action_cancel()

    def process_order_status_shopee(self, data):
        """
        Processes the order status from Shopee and updates or creates the corresponding sale order in Odoo.
        Args:
            data (dict): A dictionary containing the order details from Shopee. Expected keys include:
                - 'order_sn' (str): The order serial number.
                - 'order_status' (str): The status of the order.
                - 'update_time' (int): The timestamp of the last update.
                - 'buyer_user_id' (str): The ID of the buyer.
                - 'recipient_address' (dict): The recipient's address details, including 'name' and 'phone'.
                - 'item_list' (list): A list of items in the order, where each item is a dictionary containing:
                    - 'item_id' (str): The ID of the item.
                    - 'item_name' (str): The name of the item.
                    - 'model_discounted_price' (float): The discounted price of the item.
                    - 'item_sku' (str): The SKU of the item.
                    - 'model_quantity_purchased' (int): The quantity purchased of the item.
                - 'create_time' (int): The timestamp of when the order was created.
                - 'message_to_seller' (str): Any message from the buyer to the seller.
        Returns:
            None
        """
        
        order = self.check_order_shopee_exist(data.get('order_sn'))
        status = data.get('order_status','')
        if order:
            order.write({
                'shopee_status': status,
            })
            order._update_order_shopee(order, status, datetime.fromtimestamp(data.get('update_time', 0)))
            
        else:
            custommer_id = self.check_partner_shopee_id(
                data['buyer_user_id'],
                data['recipient_address']['name'],
                data['recipient_address']['phone'],
            )
            
            line_items = data.get('item_list', [])
            prepared_line_items = []
            pricelist = self.pricelist_id if self.pricelist_id else self.env['ir.config_parameter'].sudo().get_param('shopee_connector.pricelist_id')
            product_ecommerce_model = self.env['product.ecommerce']
            
            for item in line_items:
                shopee_product_id = product_ecommerce_model.search([
                    ('platform', '=', 'shopee'),
                    ('product_shopee_id', '=', item['item_id']),
                ], limit =1)
                
                if not shopee_product_id:
                    product_tmp = self.env['product.product'].create({
                        'name': item.get('item_name', ''),
                        'list_price': item.get('model_discounted_price', ''),
                        'default_code': item.get('item_sku', ''),
                        'type': 'product',
                    })
                    vals = {
                        'name':item.get('item_name', ''),
                        'price': item.get('model_discounted_price', ''), #! special case for Santagift
                        'sku': item.get('item_sku', ''),
                        'quantity':item.get('model_quantity_purchased', ''),
                        'platform': 'shopee',
                        'product_shopee_id': item.get('item_id', ''),
                        'product_id': product_tmp.id,
                    }
                    shopee_product_id = product_ecommerce_model.create(vals)
                    
                price_unit = shopee_product_id.product_id.list_price
                if pricelist:
                    price_unit = self.pricelist._get_product_price(shopee_product_id.product_id, item.get('model_quantity_purchased', 0))
                
                prepared_line_items.append({
                    'product_id': shopee_product_id.product_id.id,
                    'product_uom_qty': item.get('model_quantity_purchased', 0),
                    'price_unit': price_unit,
                    'platform_price': item.get('model_discounted_price', 0),
                    'tax_id': [(6, 0, [])],
                })
            
            create_date = datetime.fromtimestamp(data.get('create_time', 0))    
            if prepared_line_items:
                pre_data = {
                    'name': data.get('order_sn', ''),
                    'partner_id': custommer_id,
                    'shopee_order_id': data.get('order_sn', ''),
                    'note':data.get('message_to_seller', ''),
                    'order_line': [(0,0,line) for line in prepared_line_items],
                    'ecommerce_platform': 'shopee',
                    'shopee_status': status,
                    'create_time_platform': create_date,
                }
            order_shopee = self.env['sale.order'].create(pre_data)
            order_shopee._update_order_shopee(order_shopee, status, create_date)

    @api.model
    def update_existing_records_index(self):
        self.env.cr.execute("REINDEX TABLE sale_order")

    def common_params_shopee(self):
        config_param = self.env['ir.config_parameter'].sudo()
        host = config_param.get_param('shopee_connector.url_shopee', '')
        access_token = config_param.get_param('shopee_connector.token_shopee', '')
        partner_id = int(config_param.get_param('shopee_connector.partner_id_shopee', 0))
        shop_id = int(config_param.get_param("shopee_connector.shopee_shop_id", 0))
        partner_key = config_param.get_param('shopee_connector.partner_key_shopee', '').encode()
        return host, access_token, partner_id, shop_id, partner_key    
       
    def _action_process_document_download(self, order_sn, package_number):
        """
        Processes the document download for a given Shopee order.
        This method sends a POST request to the Shopee API to download the shipping document
        for the specified order and package number.
        Args:
            order_sn (str): The order serial number.
            package_number (str): The package number associated with the order.
        Returns:
            bytes: The content of the downloaded document if the request is successful.
            None: If the request fails or an exception occurs.
        Raises:
            Exception: If an error occurs during the process, it is logged and None is returned.
        """
        
        _logger.info('Get Document Download Shopee: %s', order_sn)
        try:
            host, access_token, partner_id, shop_id, partner_key = self.common_params_shopee()
            # POST
            path = '/api/v2/logistics/download_shipping_document'
            url = f"{host}{path}"
            timest = int(fields.Datetime.now().timestamp())
            params = {
                'access_token': access_token,
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timest
            }
            payload = json.dumps({
            "order_list": [
                {
                "order_sn": order_sn,
                "package_number": package_number,
                }
            ],
            "shipping_document_type": "NORMAL_AIR_WAYBILL"
            })

            headers = {
                'Content-Type': 'application/json'
            }

            tmp_base_string = "%s%s%s%s%s" % (partner_id, path, timest, access_token, shop_id)
            base_string = tmp_base_string.encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            params['sign'] = sign

            response = requests.post(url, params=params, data=payload, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                _logger.error("Failed to download document %s: %s", order_sn, response.text)
                return None
        except Exception as e:
            _logger.error("ERROR _action_process_document_download: %s", e)

    def _action_create_shipping_document(self, order_sn, tracking_number):
        """
        Create a shipping document for a Shopee order.
        This method sends a request to the Shopee API to create a shipping document for the specified order.
        Args:
            order_sn (str): The order serial number.
            tracking_number (str): The tracking number for the shipment.
        Returns:
            dict: The response data from the Shopee API if the request is successful.
            None: If the request fails.
        Raises:
            Exception: If there is an error during the request process.
        Logs:
            Info: Logs the creation attempt and success response.
            Error: Logs any exceptions that occur during the process.
        """
        
        _logger.info('Create Shipping Document Shopee: %s', order_sn)
        try:
            host, access_token, partner_id, shop_id, partner_key = self.common_params_shopee()
            timest = int(time.time())
            path = '/api/v2/logistics/create_shipping_document'
            url = f"{host}{path}"
            params = {
                'access_token': access_token,
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timest
            }
            tmp_base_string = "%s%s%s%s%s" % (partner_id, path, timest, access_token, shop_id)
            base_string = tmp_base_string.encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            params['sign'] = sign
            payload = json.dumps({
                "order_list": [
                    {
                        "order_sn": order_sn,
                        "shipping_document_type": "NORMAL_AIR_WAYBILL",
                        "tracking_number": tracking_number
                    }
                ]
            })
            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.post(url, params=params, headers=headers, data=payload)
            if response:
                data = response.json()
                _logger.info("SUCCESS Create Shipping Document Shopee: %s", data)
                return data
            else:
                return None
        except Exception as e:
            _logger.error("ERROR _action_create_shipping_document: %s", e)

    def _action_get_shipping_document_result(self, order_sn, package_number):
        """
        Fetches the shipping document result from Shopee for a given order and package number.
        This method constructs the necessary parameters and headers, signs the request, and sends a POST request
        to Shopee's logistics API to retrieve the shipping document result.
        Args:
            order_sn (str): The order serial number.
            package_number (str): The package number.
        Returns:
            dict: The response data from Shopee if the request is successful.
            None: If the request fails or an exception occurs.
        Raises:
            Exception: Logs the error if any exception occurs during the process.
        """
        
        _logger.info('Get Shipping Document Result Shopee: %s', order_sn)
        try:
            host, access_token, partner_id, shop_id, partner_key = self.common_params_shopee()
            timest = int(time.time())
            path = '/api/v2/logistics/get_shipping_document_result'
            url = f"{host}{path}"
            params = {
                'access_token': access_token,
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timest
            }
            tmp_base_string = "%s%s%s%s%s" % (partner_id, path, timest, access_token, shop_id)
            base_string = tmp_base_string.encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            params['sign'] = sign
            payload = json.dumps({
            "order_list": [
                {
                "order_sn": order_sn,
                "package_number": package_number,
                "shipping_document_type": "NORMAL_AIR_WAYBILL"
                }
            ]
            })
            headers = {
            'Content-Type': 'application/json'
            }

            response = requests.post(url, params=params, headers=headers, data=payload)
            if response:
                data = response.json()
                _logger.info("SUCCESS Get Shipping Document Result Shopee: %s", data)
                return data
            else:
                return None
        except Exception as e:
            _logger.error("ERROR _action_get_shipping_document_result: %s", e)
    
    def write(self, vals):
        """
        Overrides the write method to handle the creation and attachment of a shipping document
        when the 'shopee_tracking_number' is present in the values to be written.
        Args:
            vals (dict): Dictionary of values to be written to the record.
        Returns:
            bool: True if the write operation was successful, False otherwise.
        Workflow:
            1. Checks if 'shopee_tracking_number' is in vals.
            2. Calls _action_create_shipping_document to create the shipping document.
            3. If the document creation is successful, attempts to get the shipping document result.
            4. If the document status is "READY", downloads the document and creates an attachment.
            5. Adds the attachment ID to vals under 'tracking_document_id'.
            6. Logs an error message if the document creation fails.
            7. Calls the super method to perform the actual write operation.
        """
        
        if 'shopee_tracking_number' in vals:
            shopee_order_id = self.shopee_order_id
            shopee_tracking_number = vals.get('shopee_tracking_number')
            shopee_package_number = vals.get('shopee_package_number')

            document_ready = self._action_create_shipping_document(shopee_order_id, shopee_tracking_number)
            if not document_ready.get('error'):
                for _ in range(5):
                    document_result = self._action_get_shipping_document_result(
                        shopee_order_id, shopee_package_number)
                    result_list = document_result.get("response", {}).get("result_list", [{}])
                    if result_list[0].get("status") == "READY":
                        file_content = self._action_process_document_download(
                            shopee_order_id, shopee_package_number)
                        
                        file_name = 'shopee_shipping_label_%s.pdf' % self.shopee_order_id
                        attachment = self.env['ir.attachment'].create({
                            'name': file_name,
                            'type': 'binary',
                            'datas': base64.b64encode(file_content),
                            'res_model': 'sale.order',
                            'res_id': self.id,
                            'mimetype': 'application/pdf',
                        })
                        vals['tracking_document_id'] = attachment.id
                        
                        # vals['note_document'] = file_content
                        
                        break
                    time.sleep(6)
            else:
                _logger.info("Failed to create shipping document: %s", document_ready)
        return super(SaleOrder, self).write(vals)
       
    #_________ cron fix data________
    def _cron_fix_data_document_tracking_shopee(self, date_from, date_to):
        _logger.info('Cron Fix Data Document Tracking Shopee')
        orders = self.env['sale.order'].search([
            ('ecommerce_platform', '=', 'shopee'),
            ('create_time_platform', '>=', date_from), 
            ('create_time_platform', '<=', date_to),
            ('shopee_tracking_number', '!=', False),
            ('note_document', '!=', False),
            ('tracking_document_id', '=', False),
        ])
        if not orders:
            _logger.info('No data found')
            return False
        for order in orders:
            file_content = order.note_document
            soup = BeautifulSoup(file_content, 'html.parser')
            pdf_content = soup.get_text()
            if isinstance(pdf_content, str):
                pdf_content = pdf_content.encode('utf-8')
            file_name = 'shopee_shipping_label_%s.pdf' % order.shopee_order_id
            attachment = self.env['ir.attachment'].create({
                'name': file_name,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': 'application/pdf',
            })
            order.write({'tracking_document_id': attachment.id})
            _logger.info('SUCCESS Fix Data Document Tracking Shopee: %s', order.shopee_order_id)
        return True
