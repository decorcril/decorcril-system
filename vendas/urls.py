from django.urls import path

from catalogo import views
from vendas.views import order_pdf
from .views.autocomplete import ClientAutocompleteView, ProductAutocompleteView
from .views.order_view import (
    OrderDetailView,
    OrderListView,
    OrderCreateView,
    OrderConfirmView,
    OrderDeleteView,
    OrderItemListView,
    OrderItemCreateView,
    OrderItemUpdateView,
    OrderItemDeleteView,
    
)
from .views.payment_view import (
    PaymentListView,
    PaymentCreateView,
    PaymentDeleteView,
)

app_name = "vendas"

urlpatterns = [

    # =====================
    # Autocomplete
    # =====================
    path("autocomplete/clientes/", ClientAutocompleteView.as_view(), name="autocomplete_client"),
    path("autocomplete/produtos/", ProductAutocompleteView.as_view(), name="autocomplete_product"),

    # =====================
    # Pedidos
    # =====================
    path("orders/", OrderListView.as_view(), name="order_list"),
    path("orders/create/", OrderCreateView.as_view(), name="order_create"),
    path("orders/<int:pk>/confirm/", OrderConfirmView.as_view(), name="order_confirm"),
    path("orders/<int:pk>/delete/", OrderDeleteView.as_view(), name="order_delete"),
    path("orders/<int:pk>/detail/", OrderDetailView.as_view(), name="order_detail"),


    # =====================
    # Itens do Pedido
    # =====================
    path("orders/<int:order_id>/items/", OrderItemListView.as_view(), name="order_items"),
    path("orders/<int:order_id>/items/add/", OrderItemCreateView.as_view(), name="orderitem_add"),
    path("orders/items/<int:item_id>/edit/", OrderItemUpdateView.as_view(), name="orderitem_edit"),
    path("orders/items/<int:item_id>/delete/", OrderItemDeleteView.as_view(), name="orderitem_delete"),

    # =====================
    # Pagamentos
    # =====================
    path("orders/<int:pk>/payments/", PaymentListView.as_view(), name="order_payments"),
    path("orders/<int:pk>/payments/add/", PaymentCreateView.as_view(), name="payment_create"),
    path("payments/<int:payment_pk>/delete/", PaymentDeleteView.as_view(), name="payment_delete"),

    # ==================
    # PDF
    # ==================
    path("orders/<int:pk>/pdf/", order_pdf, name="order_pdf"),
]