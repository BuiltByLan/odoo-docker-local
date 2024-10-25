import logging
from odoo import fields, models, api, _
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class DeliveryAPILog(models.Model):
    _name = 'delivery.api.log'
    _description = 'Delivery API Log'
    _order = 'id desc'
    _rec_name = 'transporter_id'

    transporter_id = fields.Many2one(
    'res.partner', string='Transporter',
    )
    response = fields.Text(string='Response')
    request = fields.Text(string='Request')
    is_success = fields.Boolean(default=False)

    @api.model
    def autovacuum(self, days, limit=None):
        days = (days > 0) and int(days) or 0
        deadline = datetime.now() - timedelta(days=days)
        records = self.search(
            [("create_date", "<=", fields.Datetime.to_string(deadline))],
            limit=limit,
            order="create_date asc",
        )
        nb_records = len(records)
        with self.env.norecompute():
            records.unlink()
        _logger.info("AUTOVACUUM - %s '%s' records deleted", nb_records, 'delivery.api.log')
        return True
