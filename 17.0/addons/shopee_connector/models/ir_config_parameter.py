import hmac
import time
import hashlib
import requests
import json
from datetime import datetime, timedelta

from odoo import models, _
from odoo.exceptions import UserError
from urllib.parse import unquote


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def get_token_account_level(self, code, partner_id, tmp_partner_key, main_account_id):
        timest = int(time.time())
        host = self.env['ir.config_parameter'].sudo().get_param('shopee_connector.url_shopee', '')
        path = "/api/v2/auth/token/get"
        body = {"code": code, "main_account_id": main_account_id, "partner_id": partner_id}
        tmp_base_string = "%s%s%s" % (partner_id, path, timest)
        base_string = tmp_base_string.encode()
        partner_key = tmp_partner_key.encode()
        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
        url = host + path + "?partner_id=%s&timestamp=%s&sign=%s" % (partner_id, timest, sign)

        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=body, headers=headers)
        ret = json.loads(resp.content)
        access_token = ret.get("access_token")
        new_refresh_token = ret.get("refresh_token")
        return access_token, new_refresh_token
    
    def get_access_token_shop_level(self, shop_id, partner_id, tmp_partner_key, refresh_token):
        timest = int(time.time())
        host = "https://partner.shopeemobile.com"
        path = "/api/v2/auth/access_token/get"
        body = {"shop_id": shop_id, "refresh_token": refresh_token,"partner_id":partner_id}
        tmp_base_string = "%s%s%s" % (partner_id, path, timest)
        base_string = tmp_base_string.encode()
        partner_key = tmp_partner_key.encode()
        sign = hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
        url = host + path + "?partner_id=%s&timestamp=%s&sign=%s" % (partner_id, timest, sign)
        # print(url)
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=body, headers=headers)
        ret = json.loads(resp.content)
        access_token = ret.get("access_token")
        new_refresh_token = ret.get("refresh_token")
        return access_token, new_refresh_token

    def action_refresh_token_shopee(self):
        partner_id = int(self.env["ir.config_parameter"].sudo().get_param("shopee_connector.partner_id_shopee", 0))
        tmp_partner_key = self.env["ir.config_parameter"].sudo().get_param("shopee_connector.partner_key_shopee", False)
        shop_id = int(self.env["ir.config_parameter"].sudo().get_param("shopee_connector.shopee_shop_id", 0))
        refresh_token_shopee = self.env["ir.config_parameter"].sudo().get_param("shopee_connector.refresh_token_shopee", "")
        try:
            access_token, new_refresh_token = self.get_access_token_shop_level(
                shop_id, partner_id, tmp_partner_key, refresh_token_shopee)
        except Exception as e:
            raise UserError(_('Get Code Error: %s' % e))

        if access_token and new_refresh_token:
            self.env["ir.config_parameter"].sudo().set_param("shopee_connector.refresh_token_shopee", new_refresh_token)
            self.env["ir.config_parameter"].sudo().set_param("shopee_connector.token_shopee", access_token)

    def action_get_token_shopee(self):
        partner_id = int(self.env["ir.config_parameter"].sudo().get_param("shopee_connector.partner_id_shopee", 0))
        tmp_partner_key = self.env["ir.config_parameter"].sudo().get_param("shopee_connector.partner_key_shopee", False)
        url = unquote(self.value)
        try:
            code = url.split("code=")[1].split("&")[0]
            shop_id = int(url.split("main_account_id=")[1].split("&")[0])
            access_token, new_refresh_token = self.get_token_account_level(
                code, partner_id, tmp_partner_key, shop_id)
        except Exception as e:
            raise UserError(_('Get Code Error: %s' % e))

        if access_token and new_refresh_token:
            date_connect_shopee = (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
            self.env["ir.config_parameter"].sudo().set_param("shopee_connector.refresh_token_shopee", new_refresh_token)
            self.env["ir.config_parameter"].sudo().set_param("shopee_connector.token_shopee", access_token)
            self.env["ir.config_parameter"].sudo().set_param("shopee_connector.date_connect_shopee", date_connect_shopee)
            self.env["ir.config_parameter"].sudo().set_param("shopee_connector.shop_id", shop_id)

