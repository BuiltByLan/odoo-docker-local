# -*- coding: utf-8 -*-
from ...lazop.base import LazopClient, LazopRequest


def get_lazada_credentials(env):
    app_key = env['ir.config_parameter'].sudo().get_param('lazada_connector.app_key_lazada')
    app_secret = env['ir.config_parameter'].sudo().get_param('lazada_connector.app_secret_lazada')
    auth_service = env['ir.config_parameter'].sudo().get_param('lazada_connector.auth_service_lazada')
    return app_key, app_secret, auth_service

def Createtoken(env, code):
    app_key, appSecret, authService = get_lazada_credentials(env)
    
    client = LazopClient(authService, app_key, appSecret)
    request = LazopRequest('/auth/token/create')
    request.add_api_param('code', code)
    # request.add_api_param('uuid', '38284839234')
    response = client.execute(request)
    print("1    :",response.type)
    # response code, 0 is no error
    print("2    :",response.code)
    # response error message
    print("3    :",response.message)
    # response unique id
    print("4    :",response.request_id)
    print("5    :",response.body)
    json_payload = response
    print("6    :",json_payload.body)
    # {'access_token': '50000200c39tIBDoxryhabGXemviUsDYhdu6lUvEHiQgVhyzHrZ13c0a7148yLGN', 'country': 'vn', 'refresh_token': '500012016391rNgire0we9CEr8q0WgGfPj0grVBEYDvoANw2x0P1c9f784ev5bUf', 'account_platform': 'seller_center', 'refresh_expires_in': 2592000, 'country_user_info': [{'country': 'vn', 'user_id': '200185074242', 'seller_id': '200185074242', 'short_code': 'VN33WH4M4S'}], 'expires_in': 604800, 'account': 'LzdOp_VN_test@163.com', 'code': '0', 'request_id': '2101069617117174169268061'}
    return json_payload
