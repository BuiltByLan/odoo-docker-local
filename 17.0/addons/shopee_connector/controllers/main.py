import logging

import odoo
from odoo import _, registry, http
from odoo.http import route, Controller

_logger = logging.getLogger(__name__)

class ShopeeConnector(Controller):
    @route('/webhook/shopee', type='json', auth='none', methods=['GET', 'POST'], csrf=False, cors='*', save_session=False)
    def shopee_callback_webhook(self, **kwargs):
        # Get the database name from the request
        # db_name = http.request.env.cr.dbname
        db_name = odoo.tools.config['db_name']
        with odoo.sql_db.db_connect(db_name).cursor() as cr:
            payload = http.request.get_json_data()
            _logger.info(f"Payload Shopee: {payload}")
            # Process the webhook payload
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            return env['shopee.integration'].sudo().process_webhook(payload)
        