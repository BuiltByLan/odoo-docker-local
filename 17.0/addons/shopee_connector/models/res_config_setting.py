# -*- coding: utf-8 -*-
import hmac
import time
import hashlib
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    token_shopee = fields.Char(
        "Access Token Shopee",
        config_parameter="shopee_connector.token_shopee"
    )
    refresh_token_shopee = fields.Char(
        "Refresh Token",
        config_parameter="shopee_connector.refresh_token_shopee",
        default="Get Refresh Token"
    )
    url_shopee = fields.Char(
        "Base URL Shopee",
        config_parameter="shopee_connector.url_shopee",
    )
    url_shopee_redirected = fields.Char(
        "URL Shopee Redirected",
        config_parameter="shopee_connector.url_shopee_redirected"
    ) #use when create auth url - > return url from shopee -> pass to this field
    shopee_redirect_uri = fields.Char(
        "Redirect uri",
        config_parameter="shopee_connector.shopee_redirect_uri", help='Redirect uri for callback auth from shopee' 
    ) 
    pricelist_shopee_id = fields.Many2one(
        "product.pricelist",
        "Pricelist for Shopee",
        config_parameter="shopee_connector.pricelist_id",
    )

    partner_id_shopee = fields.Char( config_parameter="shopee_connector.partner_id_shopee", string="Partner ID")
    partner_key_shopee = fields.Char( config_parameter="shopee_connector.partner_key_shopee", string="Partner Key")
    shopee_shop_id = fields.Char( config_parameter="shopee_connector.shopee_shop_id", string="Shop ID")

    def action_create_auth_url_shopee(self):
        timest = int(time.time())
        host = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.url_shopee', '')
        path = "/api/v2/shop/auth_partner"
        redirect_url = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.shopee_redirect_uri', '')
        partner_id = int(self.env['ir.config_parameter'].sudo().get_param('shopee_connector.partner_id_shopee', 0))
        tmp = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.partner_key_shopee', False)
        partner_key = tmp.encode()
        tmp_base_string = "%s%s%s" % (partner_id, path, timest)
        base_string = tmp_base_string.encode()
        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
        # generate api
        url = host + path + "?partner_id=%s&timestamp=%s&sign=%s&redirect=%s" % (
            partner_id, timest, sign, redirect_url)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
