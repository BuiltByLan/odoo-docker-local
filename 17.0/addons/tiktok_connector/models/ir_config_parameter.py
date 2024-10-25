import requests
import logging

from odoo import models, _
from .sign_api_request import get_cipher_shop_key

_logger = logging.getLogger(__name__)

class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def action_get_token_tiktok(self, host):
        headers = {
            "Content-Type": "application/json",
        }
        url = "https://auth.tiktok-shops.com/api/v2/token/get"
        try:
            app_key = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_key_tiktok', False)
            app_secret = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_secret_tiktok', False)
            auth_code = host.split("code=")[1].split("&")[0]
            params = {
                "app_key": app_key,
                "app_secret": app_secret,
                "auth_code": auth_code,
                "grant_type": "authorized_code",
            }
            res = requests.get(url, params=params, headers=headers, timeout=30)
            result = res.json()
            if res.status_code == 200:
                self.env["ir.config_parameter"].sudo().set_param(
                    "tiktok_connector.token_tiktok", result.get("data").get("access_token")
                )
                self.env["ir.config_parameter"].sudo().set_param(
                    "tiktok_connector.refresh_token_tiktok",
                    result.get("data").get("refresh_token"),
                )
        except Exception as e:
            _logger.error("ERROR action_get_token_tiktok: %s", e)

    def action_refresh_token_tiktok(self):
        headers = {
            "Content-Type": "application/json",
        }
        url = 'https://auth.tiktok-shops.com/api/v2/token/refresh'
        try:
            app_key = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_key_tiktok', False)
            refresh_token = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.refresh_token_tiktok', False)
            app_secret = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_secret_tiktok', False)
            params = {
                "app_key": app_key, 
                "app_secret": app_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                }
            res = requests.get(url, params=params, headers=headers, timeout=30)
            result = res.json()
            if result:
                self.env['ir.config_parameter'].sudo().set_param('tiktok_connector.token_tiktok', result.get('data').get('access_token'))
                self.env['ir.config_parameter'].sudo().set_param('tiktok_connector.refresh_token_tiktok', result.get('data').get('refresh_token'))
        except Exception as e:
            _logger.error("ERROR action_refresh_token_tiktok: %s", e)
        
    def action_get_active_shop_cipher(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.url_tiktok', '')
        token = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.token_tiktok', '')
        app_key = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_key_tiktok', False)
        app_secret = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.app_secret_tiktok', False)
        try:
            shops = get_cipher_shop_key(app_key, app_secret, token, base_url).get("data").get("shops")
            if shops:
                for shop in shops:
                    self.env['ir.config_parameter'].sudo().set_param('tiktok_connector.shop_id', shop.get("id"))
                    self.env['ir.config_parameter'].sudo().set_param('tiktok_connector.shop_cipher_key', shop.get("cipher"))
        except Exception as e:
            _logger.error("ERROR action_get_active_shop_cipher: %s", e)
