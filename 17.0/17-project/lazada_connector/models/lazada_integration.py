# -*- coding: utf-8 -*-
from odoo import models, api, _
from ..lazop.base import LazopClient, LazopRequest
import json
import logging

_logger = logging.getLogger(__name__)

class LazadaIntegration(models.Model):
    _name = 'lazada.integration'
    _description = 'Lazada Integration'

    @api.model
    def process_webhook(self, payload):
        self.env['lazada.message'].create({
            'name': 'LAZADA  - ' + str(payload.get('timestamp')),
            'type_request': payload.get('message_type'),
            'seller_id': payload.get('seller_id'),
            'timestamp': payload.get('timestamp'),
            'data_raw': json.dumps(payload)
        })
        
        type_request = payload.get('message_type')
        if type_request == 0:
            if payload.get('data').get('order_status') == 'pending':
                return True
            self.process_order_status_update(payload)
        return True
    
    def common_params(self):
        """
        Returns:
            tuple: access_token, appkey, appSecret, url
        """
        config_param = self.env['ir.config_parameter'].sudo()
        access_token = config_param.get_param('lazada_connector.access_token')
        appkey = config_param.get_param('lazada_connector.app_key_lazada')
        appSecret = config_param.get_param('lazada_connector.app_secret_lazada')
        url = config_param.get_param('lazada_connector.api_service_lazada')
        
        return access_token, appkey, appSecret, url
        
    def process_order_lines_item(self, order):
        """
        Args:
            order (str): The order ID.
        Returns:
            dict: The response data containing order lines.
        """
        _logger.info('Order Lines Item: %s', order)
        access_token, appkey, appSecret, url = self.common_params()
        client = LazopClient(url, appkey, appSecret)
        path = '/order/items/get'
        request = LazopRequest(path, 'GET')
        request.add_api_param('order_id', order)
        response = client.execute(request, access_token)
        return response.body.get('data')
    
    def process_order_status_update(self, payload):
        """
        Args:
            payload (dict): The payload containing order status update.
        """
        _logger.info('Lazada Order Status Update: %s', payload)

        order = payload.get('data').get('trade_order_id')
        access_token, appkey, appSecret, url = self.common_params()
        client = LazopClient(url, appkey ,appSecret)
        path = '/order/get' 
        
        request = LazopRequest(path, 'GET')
        request.add_api_param('order_id', order)
        response = client.execute(request, access_token)
        
        _logger.info('Response: %s', response)
        if response.body.get('data'):
            order_data = response.body.get('data')
            _logger.info('Order Data: %s', order_data)
            lines_data = self.process_order_lines_item(order)
            self.env['sale.order'].process_order_status_lazada(order_data, lines_data)
        else:
            _logger.error('Lazada Order Status Update Error: %s', response)
            return None
        
    def get_pack_fulfillment(self, order):
        """
        Args:
            order (str): The order ID.
        Returns:
            dict: The response data containing pack fulfillment.
        """
        _logger.info('Pack Fulfillment: %s', order)
        #TODO get order_item_list, delivery_type, shipment_provider_code, shipping_allocate_type
        order_id = order
        order_item_list = []
        delivery_type = 'dropship'
        shipment_provider_code = ''
        shipping_allocate_type = ''
        
        access_token, appkey, appSecret, url = self.common_params()
        path = '/order/fulfill/pack'
        client = LazopClient(url, appkey ,appSecret)
        request = LazopRequest(path)
        #params
        # {
        #   "pack_order_list": [
        #     {
        #       "order_item_list": ["[]", "[]"],
        #       "order_id": "id"
        #     },
        #     {
        #       "order_item_list": ["[]", "[]"],
        #       "order_id": "id"
        #     }
        #   ],
        #   "delivery_type": "dropship",
        #   "shipment_provider_code": "FM49",
        #   "shipping_allocate_type": "TFS"
        # }
        json_string = f'{{"pack_order_list":[{{"order_item_list":{order_item_list},"order_id":"{order_id}"}}],"delivery_type":"{delivery_type}","shipment_provider_code":"{shipment_provider_code}","shipping_allocate_type":"{shipping_allocate_type}"}}'

        request.add_api_param('packReq', json_string)
                
        response = client.execute(request, access_token)
        print(response.type)
        print(response.body)
        return response.body.get('data')
    
    