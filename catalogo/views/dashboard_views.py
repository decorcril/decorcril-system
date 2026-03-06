from django.shortcuts import render
from django.utils.timezone import now

from vendas.models.order import Order
from ..models import Category, SinglePiece
from clientes.models import Client
from ..decorators import group_required


@group_required("Supervisor", "Vendedor")
def dashboard(request):
    user = request.user

    # =========================
    # Permissões
    # =========================
    is_supervisor = user.groups.filter(name="Supervisor").exists()
    is_vendedor = user.groups.filter(name="Vendedor").exists()

    # =========================
    # Queries base
    # =========================
    categories = Category.objects.filter(is_active=True)
    products = SinglePiece.objects.filter(is_active=True)

    today = now().date()

    # =========================
    # Contexto
    # =========================
    context = {
        # Listagens reduzidas
        "categories": categories[:5],
        "products": products[:5],

        # Totais gerais
        "total_categories": categories.count(),
        "total_products": products.count(),
        "total_clients": Client.objects.count(),
       "total_orders": Order.objects.filter(created_by=user).count(),

        # Permissões
        "is_supervisor": is_supervisor,
        "is_vendedor": is_vendedor,

        # Grupo atual
        "user_group": (
            user.groups.first().name if user.groups.exists() else "Sem grupo"
        ),
    }

    return render(request, "catalogo/dashboard/index.html", context)