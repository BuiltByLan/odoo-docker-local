import json
import requests
import hmac
import hashlib
import time

from odoo import models, fields, api, _
from datetime import datetime

import logging

_logger = logging.getLogger(__name__)


class ShopeeIntegration(models.Model):
    _name = 'shopee.integration'
    _description = 'Shopee Integration'

    @api.model
    def process_webhook(self, payload):
        """
        Processes incoming webhook payload from Shopee and performs actions based on the payload data.
        Args:
            payload (dict): The webhook payload containing information about the event.
        Returns:
            bool: True if the webhook was processed successfully, False otherwise.
        Raises:
            Exception: If an error occurs during processing.
        The payload is expected to have the following structure:
        {
            'code': int,          # Event code
            'timestamp': str,     # Event timestamp
            'data': dict,         # Event data containing order information
            'shop_id': int        # Shop identifier
        }
        The method performs the following actions based on the event code:
        - If code is 3 and status is 'IN_CANCEL', logs success and returns True.
        - If code is 3 and status is not 'IN_CANCEL', processes order status push and returns True.
        - If code is 4, processes tracking number update and returns True.
        - Logs and raises an exception if an error occurs during processing.
        """
        try:
            # Extract payload data
            code = payload.get('code')
            timestamp = payload.get('timestamp')
            data = payload.get('data', {})
            ordersn = data.get('ordersn', '')
            status = data.get('status', '')
            shop_id = payload.get('shop_id')
            data_raw = json.dumps(payload)
            
            self.env['shopee.message'].create({
            'name': f'SHOPEE {code} - {timestamp}',
            'code_request':code,
            'order_sn': ordersn if data else 'NULL',
            'status_order': status if data else 'NULL',
            'shop_id': shop_id,
            'timestamp': timestamp,
            'data_raw': data_raw
            })

            #TODO comment action to check get message
            if code == 3:
                if status == 'IN_CANCEL':
                    _logger.info("SUCCESS Order Shopee Webhook: %s", ordersn)
                    return True
                self._action_process_order_status_push(ordersn)
                return True
            elif code == 4:
                self._action_process_tracking_number_by_webhook(ordersn, data_raw)
                _logger.info("SUCCESS Tracking Number Shopee Update: %s", ordersn)
                return True
            return True
        except Exception as e:
            _logger.error("ERROR process_webhook: %s", e)

    def common_params_shopee(self):
        config_param = self.env['ir.config_parameter'].sudo()
        host = config_param.get_param('shopee_connector.url_shopee', '')
        access_token = config_param.get_param('shopee_connector.token_shopee', '')
        partner_id = int(config_param.get_param('shopee_connector.partner_id_shopee', 0))
        shop_id = int(config_param.get_param("shopee_connector.shopee_shop_id", 0))
        partner_key = config_param.get_param('shopee_connector.partner_key_shopee', '').encode()
        return host, access_token, partner_id, shop_id, partner_key

    def _action_process_order_status_push(self, order_sn):
        try:
            # Retrieve configuration parameters once and store them in variables
            host, access_token, partner_id, shop_id, partner_key = self.common_params_shopee()

            path = '/api/v2/order/get_order_detail'
            url = f"{host}{path}"
            timest = int(fields.Datetime.now().timestamp())
            params = {
                'access_token': access_token,
                'order_sn_list': order_sn,
                'partner_id': partner_id,
                'request_order_status_pending': 'true',
                'response_optional_fields': 'buyer_user_id,buyer_username,estimated_shipping_fee,recipient_address,actual_shipping_fee,goods_to_declare,note,note_update_time,item_list,pay_time,dropshipper, dropshipper_phone,split_up,buyer_cancel_reason,cancel_by,cancel_reason,actual_shipping_fee_confirmed,buyer_cpf_id,fulfillment_flag,pickup_done_time,package_list,shipping_carrier,payment_method,total_amount,buyer_username,invoice_data,no_plastic_packing,order_chargeable_weight_gram,edt',
                'shop_id': shop_id,
                'timestamp': timest
            }

            base_string = f"{partner_id}{path}{timest}{access_token}{shop_id}".encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            params['sign'] = sign

            response = requests.get(url, params=params)
            if response.status_code == 200:
                order_list = response.json().get('response', {}).get('order_list', [])
                if order_list:
                    data = order_list[0]
                    self.env['sale.order'].process_order_status_shopee(data)

            _logger.info("SUCCESS Sale Order Shopee Update: %s", order_sn)
        except Exception as e:
            _logger.error("ERROR _action_process_order_status_push: %s", e)
            return None

    def _action_process_tracking_number(self, order_sn):
        _logger.info('Get Tracking Number Shopee By API')
        try:
            host, access_token, partner_id, shop_id, partner_key = self.common_params_shopee()

            path = '/api/v2/logistics/get_tracking_number'
            url = f"{host}{path}"
            timest = int(fields.Datetime.now().timestamp())
            params = {
                'access_token': access_token,
                'order_sn': order_sn,
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timest
            }

            base_string = f"{partner_id}{path}{timest}{access_token}{shop_id}".encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            params['sign'] = sign

            max_retries = 5
            retry_delay = 30
            
            for temp in range(max_retries):
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    tracking_number = response.json().get('response', {}).get('tracking_number')
                    if tracking_number:
                        return tracking_number
                    else:
                        _logger.warning(f"Attempt {temp + 1}/{max_retries}: Tracking number is empty, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                else:
                    _logger.error(f"Failed to get tracking number, status code: {response.status_code}")
                    return None
            _logger.error("Max retries reached, failed to get tracking number")
            return None
        except Exception as e:
            _logger.error("ERROR _action_process_tracking_number: %s", e)
    
    def _action_process_tracking_number_by_webhook(self, order_sn, data_raw):
        _logger.info('Get Tracking Number Shopee By Webhook')
        order = self.env['sale.order'].search([('shopee_order_id', '=', order_sn)], limit=1)
        if order and not order.shopee_tracking_number and not order.shopee_package_number:
            data_dict = json.loads(data_raw)
            tracking_number = data_dict.get('data').get('tracking_no')
            package_number = data_dict.get('data').get('package_number')
            order.write({
                'shopee_tracking_number': tracking_number,
                'shopee_package_number': package_number,
            })
        else:
            _logger.info("Order have data tracking: %s", order_sn)
            return

    def _action_process_tracking_info(self, order_sn):
        _logger.info('Get Tracking Info Shopee: %s', order_sn)
        try:
            host, access_token, partner_id, shop_id, partner_key = self.common_params_shopee()

            path = '/api/v2/logistics/get_tracking_info'
            url = f"{host}{path}"
            timest = int(fields.Datetime.now().timestamp())
            params = {
                'access_token': access_token,
                'order_sn': order_sn,
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timest
            }

            base_string = f"{partner_id}{path}{timest}{access_token}{shop_id}".encode()
            sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
            params['sign'] = sign

            response = requests.get(url, params=params)
            # {
            #     "error": "",
            #     "message": "",
            #     "response": {
            #         "logistics_status": "LOGISTICS_REQUEST_CREATED",
            #         "order_sn": "201214JASXYXY6",
            #         "tracking_info": [
            #             {
            #                 "update_time": 1658829595,
            #                 "description": "Sender is preparing to ship your parcel",
            #                 "logistics_status": "ORDER_CREATED"
            #             }
            #         ]
            #     },
            #     "request_id": "a3bf041ac4213ecaa0c68defda3231da"
            # }
            if response.status_code == 200:
                data = response.json().get('response', {})
            else:
                return None
        except Exception as e:
            _logger.error("ERROR _action_process_tracking_info: %s", e)
            