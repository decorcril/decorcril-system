from django.urls import path
from .views.client_views import (
    clients_list_view,
    client_update_view,
    check_document_view
)

app_name = "clientes"

urlpatterns = [
    path("", clients_list_view, name="clients_list"),
    path("editar/<int:pk>/", client_update_view, name="client_update"),
    path("verificar-documento/", check_document_view, name="check_document"),
]