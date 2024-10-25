import json

def format_webhook_message(payload):
    return {
        "type_request": payload.get("type"),
        "tts_notification_id": payload.get("tts_notification_id"),
        "shop_id": payload.get("shop_id"),
        "order_id": payload.get("data").get("order_id") if payload.get("type") == 1 else None,
        "tiktok_order_status": payload.get("data").get("order_status") if payload.get("type") == 1 else None,
        "timestamp": payload.get("timestamp"),
        "data_raw": payload.get("data")
    }