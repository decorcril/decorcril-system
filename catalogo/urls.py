from django.urls import path

from catalogo.views.composite_product_views import (
    composite_product_create,
    composite_product_update,
)
from .views.auth_views import login_view, logout_view
from .views.dashboard_views import dashboard
from .views.category_views import (
    category_list,
    category_create,
    category_update,
    category_delete,
    category_toggle,
)
from .views.product_views import (
    product_list,
    product_create,
    product_update,
    product_delete,
    product_toggle,
    product_details,
    product_edit_modal,
)

urlpatterns = [
    # Autenticação
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    # Dashboard
    path("", dashboard, name="dashboard"),
    # Categorias
    path("categorias/", category_list, name="category_list"),
    path("categorias/nova/", category_create, name="category_create"),
    path("categorias/<int:pk>/editar/", category_update, name="category_update"),
    path("categorias/<int:pk>/excluir/", category_delete, name="category_delete"),
    path("categorias/<int:pk>/toggle/", category_toggle, name="category_toggle"),
    # Produtos
    path("produtos/", product_list, name="product_list"),
    path("produtos/novo/", product_create, name="product_create"),
    # Novas URLs para modais
    path("produtos/<int:pk>/detalhes/", product_details, name="product_details"),
    path(
        "produtos/<int:pk>/editar/modal/", product_edit_modal, name="product_edit_modal"
    ),
    # URLs para ações
    path("produtos/<int:pk>/editar/", product_update, name="product_update"),
    path("produtos/<int:pk>/excluir/", product_delete, name="product_delete"),
    path("produtos/<int:pk>/toggle/", product_toggle, name="product_toggle"),
    path(
        "produtos/composto/novo/",
        composite_product_create,
        name="composite_product_create",
    ),
    path(
        "produtos/composto/<int:pk>/editar/",
        composite_product_update,
        name="composite_product_update",
    ),
]
