from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools import config


class ResConfigSettingLazada(models.TransientModel):
    _inherit = "res.config.settings"

    app_key_lazada = fields.Char("App Key", config_parameter="lazada_connector.app_key_lazada")
    app_secret_lazada = fields.Char("App Secret", config_parameter="lazada_connector.app_secret_lazada")
    api_service_lazada = fields.Char("API Service", config_parameter="lazada_connector.api_service_lazada")
    auth_service_lazada = fields.Char("Auth Service", config_parameter="lazada_connector.auth_service_lazada")
    
    auth_url_lazada = fields.Char("Auth URL", config_parameter="lazada_connector.auth_url")
    access_lazada_token = fields.Char("Access Token", config_parameter="lazada_connector.access_token")
    refresh_lazada_token = fields.Char("Refresh Token", config_parameter="lazada_connector.refresh_token")
    expires_lazada_in = fields.Char("Expires In", config_parameter="lazada_connector.expires_in")
    
    pricelist_lazada_id = fields.Many2one('product.pricelist', 'Pricelist for Lazada', config_parameter='lazada_connector.pricelist_id')
    lazada_oauth_code = fields.Char("URL Redirected", config_parameter="lazada_connector.oauth_code")
    # lazada_update_after = fields.Datetime("Update After", config_parameter="lazada_connector.update_after")
