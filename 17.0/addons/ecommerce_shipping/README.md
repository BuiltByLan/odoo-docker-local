# Ecommerce Shipping Module

## THINGS TO NOTE. THIS IS HOW LAN THINK THE CURRENT PROCESS FLOW SHOULD BE - 240927

1. Currently we only use Fulfill by TikTok / Fulfill by Shopee for Santagift.
2. We only handle the logic for this type at this time. We don't handle fulfill by seller (this may be revisited later but not at this time.)
3. To simplify things currently, the action - ARRANGE SHIPPING - is done on the platform. We do not need to create a POST mechanism to update back to the platform since this ACTION is not done in ODOO.

4. SHOPEE. When we receive webhook push for status PROCESSED on SHOPEE. We make the API call to GET tracking information and AIRWAY BILL. The API I think we need here are:
    v2.logistics.get_tracking_number
    v2.logistics.download_shipping_document
5. The remaining steps for SHOPEE should not change much after package is hand over at the warehouse.

6. TIKTOK. We also confirm on the platform. We should not have to call GET PACKAGE HANDOVER TIME SLOTS API and SHIP PACKAGE API. We should only have to call GET PACKAGE DETAIL API to GET tracking information and AIRWAY BILL when we receive the webhook notification that ARRANGE SHIPMENT has been done for an order. API:
    Get Tracking
    Get Package Shipping Document
    Get Package Detail
7. Similarly the remaining steps for TIKTOK should not change much after package is hand over at the warehouse.

8. Pickup time and courier should all be handled by the platforms at this time.
9. The goal on this release is for us to SAVE RECORD of tracking information and AIRWAY BILL internally on our own database.


This is my thoughts on how we should handle shipping information at this time. Please comment for any questions.

-Lan



## TIKTOK
`TIKTOK shipping workflow`

[link](https://partner.tiktokshop.com/docv2/page/650b2044f1fd3102b93c9178)

FULFILLMENT_BY_TIKTOK: The seller does not need to call any Fulfillment APIs to arrange fulfillment. TikTok Shop will handle the entire fulfillment process after an order is paid.

```
receive webhook -> call get order detail api -> call get package handover time slots api -> call shipping package api -> call get package shipping document api -> call get package detail api (opt)
```

1. Use the Get Package Handover Time Slots API to obtain available time slots for packages handover.
2. Use the Ship Package API to schedule the package handover time and method.
3. Use the Get Package Shipping Document API to get the shipping label.

Before calling the Create Package API, please ensure that the order has not been canceled and there is no cancellation request pending the seller's approval.
Within the remorse period (1 hour after order payment), the buyer may cancel the order without requiring the seller's approval.
After the remorse period, the buyer may request the order to be canceled, pending the seller's approval.
Please ensure that after calling the Create Package API to successfully complete the label purchase, then use the Get Package Shipping Document API to obtain the shipping label.

--- API ---
GET
Get Package Shipping Document
/fulfillment/202309/packages/{package_id}/shipping_documents
For orders shipped by TikTok Shop, this API retrieves the URL of shipping documents (shipping label and packing slip) for a package specified by the package ID. This API is only applicable to "TikTok Shipping" orders. To obtain the shipping documents URL via this API, first call "Ship Package" to ship the corresponding package.

GET
Get Package Handover Time Slots
/fulfillment/202309/packages/{package_id}/handover_time_slots
Use this API to retrieve the time slots available for pickup, drop-off, or van collection for the seller's specified package by using package ID.

GET
Get Package Detail
/fulfillment/202309/packages/{package_id}
Returns information about a package, including handover time slot, tracking number, and shipping provider information.

GET
Get Tracking
/fulfillment/202309/orders/{order_id}/tracking
This API can use the order number to obtain the corresponding logistics tracking information.

POST
Ship Package 
/fulfillment/202309/packages/{package_id}/ship
Use this API to ship a package. There are two kinds of shipping options available: TikTok Shipping or Seller Shipping.


## SHOPEE
[link](https://open.shopee.com/developer-guide/229)

1.Get the list of orders to be shipped with order status "READY_TO_SHIP" through v2.order.get_shipment_list API.

2.Call v2.logistics.get_shipping_parameter API to get the shipping parameters, seller choose any one of pick up/drop off/no integrated shipping method to ship. Call v2.logistics.ship_order to ship the order, for non-integrated channel orders, the developer should prepare the tracking number and upload it in the request body. After the API call is successful, the order status of pick up / drop off mode orders will automatically update from READY_TO_SHIP to PROCESSED, and for the non-integrated mode, order status will be immediately updated to SHIPPED.

3.After successful shipment using the Shopee integration channel, you can poll v2.logistics.get_tracking_number API to get the tracking number.

4.After getting the tracking number, you can print the airway bill. You can choose two ways: self-print or Shopee generated. The airway bill can only be printed after the order is arranged shipment successfully and before the order status is SHIPPED.

--- API ---
GET
Get a list of orders which not shipped yet
/api/v2/order/get_shipment_list
Use this api to get order list which order_status is READY_TO_SHIP to start process the whole shipping progress.

GET
Get shipping parameters
/api/v2/logistics/get_shipping_parameter
Use this api to get the parameter "info_needed" from the response to check if the order has pickup or dropoff or no integrate options. This api will also return the addresses and pickup time id options for the pickup method. For dropoff, it can return branch id, sender real name etc, depending on the 3PL requirements.

GET
Get tracking number
/api/v2/logistics/get_tracking_number
After arranging shipment (v2.logistics.ship_order) for the integrated channel, use this api to get the tracking_number, which is a required parameter for creating shipping labels. The api response can return tracking_number empty, since this info is dependent from the 3PL, due to this it is allowed to keep calling the api within 5 minutes interval, until the tracking_number is returned.

GET
/api/v2/logistics/get_tracking_info
Use this api to get the logistics tracking information of an order.

POST
Get airway bill task result
/api/v2/logistics/get_shipping_document_result
Use this api to retrieve the status of the shipping document task. Document will be available for download only after the status change to 'READY'.

POST
Download Shopee generated airway bill
/api/v2/logistics/download_shipping_document

## LAZADA
[link](https://open.lazada.com/apps/doc/doc?nodeId=29616&docId=120167)

/order/shipment/providers/get
GetShipmentProvider
Use this API to get the list of all active shipping providers, which is needed when working with the PackOrder API.

/order/package/document/get
PrintAWB
Use this API to retrieve order-related documents, only for shipping labels.
