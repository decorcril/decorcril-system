from django.shortcuts import render
from django.utils.timezone import now

from vendas.models.order import Order
from vendas.models.payment import Payment
from ..models import Category, SinglePiece
from clientes.models import Client
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    user = request.user

    is_supervisor = user.is_superuser or user.groups.filter(name="Supervisor").exists()
    is_vendedor   = user.groups.filter(name="Vendedor").exists()
    is_financeiro = is_supervisor or user.groups.filter(name="Financeiro").exists()
    is_pos_venda  = is_supervisor or user.groups.filter(name="Pos-venda").exists()

    categories = Category.objects.filter(is_active=True)
    products   = SinglePiece.objects.filter(is_active=True)

    context = {
        "categories": categories[:5],
        "products":   products[:5],

        "total_categories": categories.count(),
        "total_products":   products.count(),
        "total_clients":    Client.objects.count(),
        "total_orders":     Order.objects.filter(created_by=user).count(),
        "total_payments":   Payment.objects.count() if is_financeiro else 0,

        "is_supervisor": is_supervisor,
        "is_vendedor":   is_vendedor,
        "is_financeiro": is_financeiro,
        "is_pos_venda":  is_pos_venda,

        "user_group": user.groups.first().name if user.groups.exists() else "Sem grupo",
    }

    return render(request, "catalogo/dashboard/index.html", context)