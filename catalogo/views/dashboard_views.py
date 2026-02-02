from django.shortcuts import render
from ..models import Category, SinglePiece
from ..decorators import group_required


@group_required("Supervisor", "Vendedor")
def dashboard(request):
    # Verificar se é supervisor
    is_supervisor = request.user.groups.filter(name="Supervisor").exists()

    categories = Category.objects.filter(is_active=True)
    products = SinglePiece.objects.filter(is_active=True)

    context = {
        "categories": categories[:5],  # Apenas 5 para o dashboard
        "products": products[:5],  # Apenas 5 para o dashboard
        "total_categories": categories.count(),
        "total_products": products.count(),
        "is_supervisor": is_supervisor,
        "user_group": (
            request.user.groups.first().name
            if request.user.groups.exists()
            else "Sem grupo"
        ),
    }

    return render(request, "catalogo/dashboard/index.html", context)
