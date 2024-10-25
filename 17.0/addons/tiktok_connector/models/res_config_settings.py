# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    token_tiktok = fields.Char(
        "Access Token TikTok", 
        config_parameter="tiktok_connector.token_tiktok"
    )
    url_tiktok = fields.Char(
        "Base URL TikTok", 
        config_parameter="tiktok_connector.url_tiktok"
    )
    pricelist_id = fields.Many2one(
        "product.pricelist",
        "Pricelist for TikTok",
        config_parameter="tiktok_connector.pricelist_id",
    )
    shop_id = fields.Char(
        "Shop ID", 
        config_parameter="tiktok_connector.shop_id"
    )
    shop_cipher_key = fields.Char(
        "Shop Cipher Key",
        config_parameter="tiktok_connector.shop_cipher_key"
    )
    app_secret_tiktok = fields.Char(
        "App Secret TikTok", 
        config_parameter="tiktok_connector.app_secret_tiktok"
    )
    refresh_token_tiktok = fields.Char(
        "Refresh Token TikTok", 
        config_parameter="tiktok_connector.refresh_token_tiktok"
    )
    app_key_tiktok = fields.Char(
        "App Key TikTok", 
        config_parameter="tiktok_connector.app_key_tiktok"
    )
    url_auth_tiktok = fields.Char(
        "Auth URL TikTok", 
        config_parameter="tiktok_connector.url_auth_tiktok"
    )
    
    #? This method is called when first authenticating the TikTok account
    def get_token_tiktok_button(self):
        host = self.env['ir.config_parameter'].sudo().get_param('tiktok_connector.url_auth_tiktok', '')
        self.env['ir.config_parameter'].action_get_token_tiktok(host)
        self.env['ir.config_parameter'].action_get_active_shop_cipher()