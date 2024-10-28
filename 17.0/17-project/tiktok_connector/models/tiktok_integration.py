import json
import time
import requests
import urllib.request
import urllib.parse
import psycopg2
from psycopg2 import OperationalError, sql

from odoo import models, fields, api, _
from .sign_api_request import cal_sign, get_timestamp
from .tools import format_webhook_message

import logging

_logger = logging.getLogger(__name__)
MAX_RETRIES = 2
RETRY_DELAY = 1


class TikTokIntegration(models.Model):
    _name = 'tiktok.integration'
    _description = 'TikTok Integration'

    @api.model
    def process_webhook(self, payload):
        msg_base = format_webhook_message(payload)
        msg_base['name'] = 'TikTok Message - ' + str(msg_base.get('tts_notification_id'))
        self.env['tiktok.message'].create(msg_base)
        type_request = payload.get('type')
        status = payload.get('data').get('order_status')
        retry_count = 4
        while retry_count > 0:
            try:
                if type_request == 1:
                    if status == 'UNPAID':
                        return True
                    self.process_order_status_update(payload)
                elif type_request == 12:
                    self.process_return_order_status(payload)
                elif type_request == 6:
                    self.process_seller_deauthorization(payload)
                elif type_request == 7:
                    self.process_auth_expire(payload)
                elif type_request == 15:
                    self.process_product_information_change(payload)
                elif type_request == 16:
                    self.process_product_creation(payload)
                else:
                    _logger.info('TikTok Webhook: %s', payload)
                return True
            except OperationalError as e:
                '''
                Both Repeatable Read and Serializable isolation levels can produce errors that are designed to prevent serialization anomalies. 
                As previously stated, applications using these levels must be prepared to retry transactions that fail due to serialization errors. 
                Such an error's message text will vary according to the precise circumstances, but it will always have the SQLSTATE code 40001 (serialization_failure). 
                '''
                if e.pgcode == '40001':  # Serialization failure
                    _logger.warning('Serialization failure: retrying...')
                    retry_count -= 1
                    self.env.cr.rollback()
                else:
                    raise
        _logger.error('Failed to process webhook after retries: %s', payload)
        return False
    
    def common_params(self, path):
        config = self.env['ir.config_parameter']
        app_key = config.sudo().get_param('tiktok_connector.app_key_tiktok', '')
        shop_cipher = config.sudo().get_param('tiktok_connector.shop_cipher_key', '')
        
        params = {
            "app_key": app_key, 
            "shop_cipher": shop_cipher,
            "timestamp": get_timestamp(),
            "version": "202309",
        } 

        return params  
    
    def request_params(self):
        config = self.env['ir.config_parameter']
        base_url = config.sudo().get_param('tiktok_connector.url_tiktok', '')
        token = config.sudo().get_param('tiktok_connector.token_tiktok', '')
        app_secret = config.sudo().get_param('tiktok_connector.app_secret_tiktok', '')
        return base_url, token, app_secret
    
    def  process_data_order_by_api(self, order_id):
        _logger.info('Get Order TikTok By API')
        base_url, token, app_secret = self.request_params()
        
        path = "/order/202309/orders"
        url = f"{base_url}{path}"
        
        headers = {
             "Content-Type": "application/json",
             "x-tts-access-token": f"{token}",
        }
        
        common_params = self.common_params(path)
        common_params['ids'] = order_id
        
        params_signed = urllib.parse.urlencode(common_params)
        url_signed = f"{url}?{params_signed}"
        common_params['sign'] = cal_sign(url_signed, app_secret)
        
        response = requests.get(url, headers=headers, params=common_params, timeout=30)
        if response.status_code == 200:
            data = response.json().get('data').get('orders')[0]
            self.env['sale.order'].process_order_status_tiktok(data)
        else:
            return None
        
    def process_data_order_by_api_no_action(self, order_id):
        """
        Fetches order data from the TikTok API based on the provided order ID.
        This method constructs the necessary URL and headers, signs the request,
        and sends a GET request to the TikTok API to retrieve order information.
        If the request is successful, it returns the order data; otherwise, it returns None.
        Args:
            order_id (str): The ID of the order to be fetched.
        Returns:
            dict or None: The order data if the request is successful, otherwise None.
        """
        
        _logger.info('Recall Order TikTok By API')
        base_url, token, app_secret = self.request_params()
        
        path = "/order/202309/orders"
        url = f"{base_url}{path}"
        
        headers = {
             "Content-Type": "application/json",
             "x-tts-access-token": f"{token}",
        }
        
        common_params = self.common_params(path)
        common_params['ids'] = order_id
        
        params_signed = urllib.parse.urlencode(common_params)
        url_signed = f"{url}?{params_signed}"
        common_params['sign'] = cal_sign(url_signed, app_secret)
        
        response = requests.get(url, headers=headers, params=common_params, timeout=30)
        if response.status_code == 200:
            data = response.json().get('data').get('orders')[0]
            return data
        else:
            return None
        
       
    def process_order_status_update(self, payload):
        """
        Processes the order status update received from TikTok.
        This method handles the update of the order status based on the payload received.
        It searches for the corresponding sale order in the database using the TikTok order ID.
        If the sale order is not found, it processes the order data via an API call.
        If the sale order is found and the status has changed, it updates the sale order status
        and commits the changes to the database.
        Args:
            payload (dict): The payload containing order status update information. 
                    Expected keys are 'data', 'order_id', 'order_status', and 'update_time'.
        Raises:
            OperationalError: If there is an error processing the order status update, 
                      it logs the error and rolls back the transaction.
        Logs:
            Info: Logs the TikTok order ID after processing the update.
            Error: Logs any errors encountered during the processing of the order status update.
        """
        
        order_id = payload.get('data').get('order_id')
        status = payload.get('data').get('order_status')
        date = payload.get('data').get('update_time')
        try:
            sale_order = self.env['sale.order'].sudo().search([
                ('tiktok_order_id', '=', order_id)], limit=1)
            if not sale_order:
                self.process_data_order_by_api(order_id)
            else:
                if sale_order.tiktok_status == status:
                    self.env.cr.commit()
                    return
                else:
                    sale_order.change_sale_order_status(sale_order, status, date)
                    if status == "AWAITING_COLLECTION":
                        data = self.process_data_order_by_api_no_action(order_id)
                        tracking_number = data.get('line_items')[0].get('tracking_number')
                        package_id = data.get('packages')[0].get('id') if not sale_order.package_id else sale_order.package_id
                        sale_order.write({
                            'tiktok_status': status,
                            'tiktok_tracking_number': tracking_number,
                            'package_url': self.get_package_shipping_document(package_id)
                        })
                    else:
                        sale_order.change_sale_order_status(sale_order, status, date)
                        sale_order.write({'tiktok_status': status})
            self.env.cr.commit()

        except OperationalError as e:
            _logger.error('Error processing order status update: %s', e)
            self.env.cr.rollback()
            
        _logger.info('Sale Order TikTok Update: %s', order_id)    
        
    #TODO later
    def process_return_order_status(self, payload):
        #* {  
        #*     "type": 12,  
        #*     "tts_notification_id": "7327112393057371910",  
        #*     "shop_id": "7494049642642441621",  
        #*     "timestamp": 1644412885,  
        #*     "data": {  
        #*         "order_id": "576486316948490001",  
        #*         "return_role": "BUYER",  
        #*         "return_type": "REFUND",  
        #*         "return_status": "RETURN_OR_REFUND_REQUEST_PENDING",  
        #*         "return_id": "576486316948490001",  
        #*         "create_time": 1627587600  
        #*         "update_time": 1644412885  
        #*     }  
        #* }
        pass
    
    #TODO chỉ deauth khi user vào xoá xác thực
    def process_seller_deauthorization(self, payload):
        pass
    
    #TODO chỉ expire khi thực hiện uỷ quyền user xét thời hạn
    def process_auth_expire(self, payload):    
        pass
    
    #TODO later
    def process_product_information_change(self, payload):
        pass
    
    def process_product_creation(self, payload):
        _logger.info('New Product Creation')
        
        base_url, token, app_secret = self.request_params()
        
        product_id = payload.get('data').get('product_id')
        path = f"/product/202309/products/{product_id}"
        url = f"{base_url}{path}"
        
        headers = {
             "Content-Type": "application/json",
             "x-tts-access-token": f"{token}",
        }
        
        common_params = self.common_params(path)
        common_params['return_under_review_version'] = False
        
        params_signed = urllib.parse.urlencode(common_params)
        url_signed = f"{url}?{params_signed}"
        common_params['sign'] = cal_sign(url_signed, app_secret)
        
        response = requests.get(url, headers=headers, params=common_params, timeout=30)
        if response.status_code == 200:
            # data = response.json().get('data')
            pass
        else:
            return None
    
    def get_tiktok_package_info(self, package_id):
        _logger.info('Get Package Info TikTok: %s', package_id)
        base_url, token, app_secret = self.request_params()
        path = f"/fulfillment/202309/packages/{package_id}"
        url = f"{base_url}{path}"

        headers = {
                "Content-Type": "application/json",
                "x-tts-access-token": f"{token}",
        }

        common_params = self.common_params(path)
        params_signed = urllib.parse.urlencode(common_params)
        url_signed = f"{url}?{params_signed}"
        common_params['sign'] = cal_sign(url_signed, app_secret)

        response = requests.get(url, headers=headers, params=common_params, timeout=30)
        if response.status_code == 200:
            data = response.json().get('data')
            return data
        else:
            return None 
        
    def get_package_shipping_document(self, package_id):
        """
        Fetches the shipping document for a given TikTok package.
        This method constructs the request URL and headers, signs the request, and sends a GET request to the TikTok API to retrieve the shipping document for the specified package ID.
        Args:
            package_id (str): The ID of the package for which the shipping document is to be retrieved.
        Returns:
            str: The URL of the shipping document if the request is successful.
            None: If the request fails or the response status code is not 200.
        Raises:
            requests.exceptions.RequestException: If there is an issue with the HTTP request.
        """
        
        _logger.info('Get Document TikTok Package: %s', package_id)
        base_url, token, app_secret = self.request_params()
        path = f"/fulfillment/202309/packages/{package_id}/shipping_documents"
        url = f"{base_url}{path}"

        headers = {
                "Content-Type": "application/json",
                "x-tts-access-token": f"{token}",
        }

        common_params = self.common_params(path)
        common_params['document_type'] = 'SHIPPING_LABEL'
        common_params['document_size'] = 'A6'
        params_signed = urllib.parse.urlencode(common_params)
        url_signed = f"{url}?{params_signed}"
        common_params['sign'] = cal_sign(url_signed, app_secret)

        response = requests.get(url, headers=headers, params=common_params, timeout=30)
        if response.status_code == 200:
            # {
            #     "code": 0,
            #     "data": {
            #         "doc_url":
            # "https://open-fs-va.tiktokshop.com/wsos_v2/oec_fulfillment_doc_tts/object/wsos670354fe473bcb06?expire=1728358025&skipCookie=true&timeStamp=1728271625&sign=72a0fb75182016485a04ac623fba9b7c958f46f899e875e809e87e3ab352623e"
            #     },
            #     "message": "Success",
            #     "request_id": "202203070749000101890810281E8C70B7"
            # }
            data = response.json().get('data').get('doc_url')
            return data
        else:
            return None
        
    def post_ship_package(self, package_id):
        _logger.info('Ship Package TikTok: %s', package_id)
        base_url, token, app_secret = self.request_params()
        path = f"/fulfillment/202309/packages/{package_id}/ship"
        url = f"{base_url}{path}"

        headers = {
                "Content-Type": "application/json",
                "x-tts-access-token": f"{token}",
        }

        common_params = self.common_params(path)
        params_signed = urllib.parse.urlencode(common_params)
        url_signed = f"{url}?{params_signed}"
        common_params['sign'] = cal_sign(url_signed, app_secret)

        json_data = {
            'handover_method': 'PICKUP',
            # 'pickup_slot': {
            #     'end_time': 1623812664,
            #     'start_time': 1623812664,
            # },
            # 'self_shipment': {
            #     'shipping_provider_id': '6617675021119438849',
            #     'tracking_number': 'JX12345',
            # },
        }

        response = requests.post(url, headers=headers, params=common_params, json=json_data, timeout=30)
        if response.status_code == 200:
            data = response.json().get('data')
            return data
        else:
            return None