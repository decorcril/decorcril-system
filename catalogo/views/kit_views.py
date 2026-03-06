from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Count, Q

from catalogo.models.product_component import ProductComponent
from ..models import SinglePiece, Category
from ..forms.composite_product import CompositeProductForm
from ..decorators import group_required


# =========================
# View para abrir modal de criação de kit
# =========================
@group_required("Supervisor")
def kit_create_modal(request):

    # Produtos simples ativos
    simple_products = SinglePiece.objects.filter(is_active=True)

    # Produtos compostos ativos (kits, composições etc.)
    composite_products = SinglePiece.objects.filter(is_active=True, is_sellable=True)

    # 🔴 IMPORTANTE: evita duplicação
    simple_and_composite_products = (
        (simple_products | composite_products)
        .distinct()
        .select_related("category")
        .order_by("sku")
    )

    categories = Category.objects.filter(is_active=True)

    context = {
        "categories": categories,
        "simple_and_composite_products": simple_and_composite_products,
        "is_supervisor": request.user.groups.filter(name="Supervisor").exists(),
    }

    return render(request, "catalogo/kit/create_modal.html", context)


# =========================
# Criar kit de fato (POST)
# =========================
@group_required("Supervisor")
def kit_create(request):
    """
    Recebe o POST do formulário do modal de criação de kit
    e salva o kit + seus componentes.
    """
    if request.method == "POST":
        form = CompositeProductForm(request.POST, request.FILES)

        if form.is_valid():
            components = request.POST.getlist("components")

            if not components:
                messages.error(request, "Kit deve possuir pelo menos um componente.")
                return redirect("product_list")

            try:
                with transaction.atomic():
                    # Salva o kit
                    kit = form.save(commit=False)
                    kit.is_sellable = True
                    kit.is_kit = True
                    kit.save()

                    # Cria os componentes do kit
                    for component_id in components:
                        qty = request.POST.get(f"quantity_{component_id}", "1")
                        try:
                            qty = int(qty)
                            if qty < 1:
                                qty = 1
                        except ValueError:
                            qty = 1

                        ProductComponent.objects.create(
                            parent=kit,
                            component_id=component_id,
                            quantity=qty,
                        )

                    messages.success(
                        request,
                        f'Kit "{kit.name}" criado com sucesso com {len(components)} componente(s)!',
                    )
            except Exception as e:
                messages.error(request, f"Erro ao criar kit: {str(e)}")
        else:
            messages.error(request, "Erro no formulário do kit. Verifique os dados.")

    return redirect("product_list")
