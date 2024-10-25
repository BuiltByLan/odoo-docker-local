import requests
import json
import hmac
import hashlib
import logging

import odoo
from odoo import http, tools
from odoo.http import request, route, Controller
from odoo.addons.base_automation.models.base_automation import get_webhook_request_payload


_logger = logging.getLogger(__name__)

class LazadaConnector(Controller):
    @route('/webhook/lazada', type='json', auth='none', methods=['GET', 'POST'], csrf=False, cors='*', save_session=False)
    def lazada_callback_webhook(self, **kwargs):
        # Get the database name from the request
        db_name = odoo.tools.config['db_name']
        with odoo.sql_db.db_connect(db_name).cursor() as cr:
            payload = http.request.get_json_data()
            _logger.info(f"Payload: {payload}")
             # Respond to the webhook       
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})    
            return env['lazada.integration'].sudo().process_webhook(payload)
