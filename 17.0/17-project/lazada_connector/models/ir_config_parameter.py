from odoo import models, api
from ..models.server.access_token import Createtoken
from ..models.server.refresh_token import renewToken
from urllib.parse import unquote


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    def action_lazada_access_token(self):
        url = unquote(self.value)
        auth_code = url.split("code=")[1].split("&")[0].replace("#?", "")
        
        data_response = Createtoken(self.env, auth_code)
        access_token = data_response.body.get('access_token', '')
        refresh_token = data_response.body.get('refresh_token', '')
        expires_in = data_response.body.get('expires_in', '')
        self.env['ir.config_parameter'].set_param('lazada_connector.access_token', access_token)
        self.env['ir.config_parameter'].set_param('lazada_connector.refresh_token', refresh_token)
        self.env['ir.config_parameter'].set_param('lazada_connector.expires_in', expires_in)
        
    def action_lazada_refresh_token(self):
        refreshToken = self.env['ir.config_parameter'].sudo().get_param('lazada_connector.refresh_token')
        
        data_response = renewToken(self.env, refreshToken)
        access_token = data_response.body.get('access_token', '')
        refresh_token = data_response.body.get('refresh_token', '')
        expires_in = data_response.body.get('expires_in', '')
        self.env['ir.config_parameter'].set_param('lazada_connector.access_token', access_token)
        self.env['ir.config_parameter'].set_param('lazada_connector.refresh_token', refresh_token)
        self.env['ir.config_parameter'].set_param('lazada_connector.expires_in', expires_in)

    # def write(self, vals):
    #     res = super(IrConfigParameter, self).write(vals)
    #     if vals.get('value', False):
    #         for record in self:
    #             if record.key == 'lazada_connector.oauth_code':
    #                 record.cron_access_token()
    #     return res

    # @api.model
    # def create(self, vals):
    #     res = super(IrConfigParameter, self).create(vals)
    #     if res.key == 'lazada_connector.oauth_code':
    #         res.cron_access_token()
    #     return res
