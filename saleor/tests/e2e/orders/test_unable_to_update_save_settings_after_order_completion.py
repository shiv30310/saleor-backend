import pytest

from .. import ADDRESS_DE, DEFAULT_ADDRESS
from ..account.utils import create_customer
from ..product.utils.preparing_product import prepare_product
from ..shop.utils.preparing_shop import prepare_default_shop
from ..utils import assert_address_data, assign_permissions
from .utils import (
    draft_order_complete,
    draft_order_create,
    draft_order_update,
    order_lines_create,
    raw_draft_order_update,
)


@pytest.mark.e2e
def test_unable_to_update_save_settings_after_order_complete_CORE_0255(
    e2e_staff_api_client,
    shop_permissions,
    permission_manage_product_types_and_attributes,
    permission_manage_orders,
    permission_manage_users,
):
    # Before
    permissions = [
        *shop_permissions,
        permission_manage_product_types_and_attributes,
        permission_manage_orders,
        permission_manage_users,
    ]
    assign_permissions(e2e_staff_api_client, permissions)

    price = 10

    shop_data = prepare_default_shop(e2e_staff_api_client)
    channel_id = shop_data["channel"]["id"]
    warehouse_id = shop_data["warehouse"]["id"]
    shipping_method_id = shop_data["shipping_method"]["id"]

    (
        _product_id,
        product_variant_id,
        _product_variant_price,
    ) = prepare_product(
        e2e_staff_api_client,
        warehouse_id,
        channel_id,
        price,
    )

    customer_input = {
        "email": "test0253@com.com",
    }

    user_data = create_customer(
        e2e_staff_api_client,
        customer_input,
    )
    user_id = user_data["id"]
    user_email = user_data["email"]

    # Step 1 - Create draft order
    # use different address for shipping and billing
    billing_address = ADDRESS_DE

    draft_order_input = {
        "channelId": channel_id,
        "user": user_id,
        "shippingAddress": DEFAULT_ADDRESS,
        "billingAddress": billing_address,
        "saveShippingAddress": True,
        "saveBillingAddress": False,
    }
    data = draft_order_create(
        e2e_staff_api_client,
        draft_order_input,
    )
    order_id = data["order"]["id"]
    assert order_id is not None

    # Step 2 - Add lines to the order
    lines = [{"variantId": product_variant_id, "quantity": 1}]
    order_lines = order_lines_create(
        e2e_staff_api_client,
        order_id,
        lines,
    )
    order_product_variant_id = order_lines["order"]["lines"][0]["variant"]["id"]
    assert order_product_variant_id == product_variant_id

    # Step 3 - Update order's shipping method
    input = {"shippingMethod": shipping_method_id}
    draft_order = draft_order_update(
        e2e_staff_api_client,
        order_id,
        input,
    )
    order_shipping_id = draft_order["order"]["deliveryMethod"]["id"]
    assert order_shipping_id is not None

    # Step 4 - Complete the order
    order = draft_order_complete(e2e_staff_api_client, order_id)
    order_complete_id = order["order"]["id"]
    assert order_complete_id == order_id
    order_line = order["order"]["lines"][0]
    assert order_line["productVariantId"] == product_variant_id
    assert order["order"]["status"] == "UNFULFILLED"
    order_billing_address = order["order"]["billingAddress"]
    order_shipping_address = order["order"]["shippingAddress"]
    assert_address_data(order_billing_address, billing_address)
    assert_address_data(order_shipping_address, DEFAULT_ADDRESS)
    assert order["order"]["user"]["id"] == user_id
    assert order["order"]["userEmail"] == user_email

    # Step 5 - Try to update order's save settings
    input = {
        "billingAddress": billing_address,
        "shippingAddress": DEFAULT_ADDRESS,
        "saveShippingAddress": True,
        "saveBillingAddress": True,
    }
    response = raw_draft_order_update(e2e_staff_api_client, order_id, input)
    errors = response["errors"]
    assert len(errors) == 1
    error = errors[0]
    assert error["field"] == "id"
    assert error["code"] == "INVALID"
