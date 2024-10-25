# -*- coding: utf-8 -*-
from ...lazop.base import LazopClient, LazopRequest


def get_lazada_credentials(env):
    app_key = env['ir.config_parameter'].sudo().get_param('lazada_connector.app_key_lazada')
    app_secret = env['ir.config_parameter'].sudo().get_param('lazada_connector.app_secret_lazada')
    auth_service = env['ir.config_parameter'].sudo().get_param('lazada_connector.auth_service_lazada')
    return app_key, app_secret, auth_service

def renewToken(env, refreshToken):
    app_key, appSecret, authService = get_lazada_credentials(env)
    print(refreshToken)
    client = LazopClient(authService, app_key, appSecret)
    # create a api request set GET mehotd
    # default http method is POST
    request = LazopRequest('/auth/token/refresh')
    # simple type params ,Number ,String
    request.add_api_param('refresh_token', refreshToken)
    # request.add_api_param('uuid', '38284839234')
    response = client.execute(request)

    # full response
    print(response.body)
    json_payload = response
    print(json_payload.body)
    return json_payload
