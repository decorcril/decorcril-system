from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Q

from catalogo.models.product_component import ProductComponent
from ..models import SinglePiece, Category
from ..forms.product_forms import SinglePieceForm
from ..decorators import group_required


# =========================
# Listagem de Produtos
# =========================
@group_required("Supervisor", "Vendedor")
def product_list(request):

    # 🔹 Base queryset com contagem de uso em composições
    products = (
        SinglePiece.objects.annotate(used_in_count=Count("used_in_compositions"))
        .select_related("category")
        .order_by("sku")
    )

    categories = Category.objects.filter(is_active=True)

    # 🔎 Filtro de pesquisa
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(category__name__icontains=q)
        )

    form = SinglePieceForm()

    # 🔹 Produtos disponíveis para serem componentes
    available_products = SinglePiece.objects.filter(
        is_active=True, components__isnull=True
    ).order_by("sku")

    # 🔹 Todas as estruturas já cadastradas
    all_components = ProductComponent.objects.select_related("component", "parent")

    context = {
        "products": products,
        "categories": categories,
        "form": form,
        "is_supervisor": request.user.groups.filter(name="Supervisor").exists(),
        "is_vendedor": request.user.groups.filter(name="Vendedor").exists(),
        "query": q,
        "single_pieces": SinglePiece.objects.filter(is_active=True).order_by("sku"),
        "simple_and_composite_products": SinglePiece.objects.filter(
            is_active=True
        ).order_by("sku"),
        "available_products": available_products,
        "all_components": all_components,
    }

    return render(request, "catalogo/products/list.html", context)


# =========================
# Criar Produto
# =========================
@group_required("Supervisor")
def product_create(request):
    if request.method == "POST":
        form = SinglePieceForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Produto "{product.name}" criado com sucesso!')
        else:
            messages.error(request, "Erro ao criar produto. Verifique os dados.")
    return redirect("product_list")


# =========================
# Atualizar Produto
# =========================
@group_required("Supervisor")
def product_update(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)

    if request.method == "POST":
        form = SinglePieceForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(
                request, f'Produto "{product.name}" atualizado com sucesso!'
            )
        else:
            messages.error(request, "Erro ao atualizar produto. Verifique os dados.")

    return redirect("product_list")


# =========================
# Deletar Produto
# =========================
@group_required("Supervisor")
@require_POST
def product_delete(request, pk):

    product = SinglePiece.objects.filter(pk=pk).first()

    if not product:
        messages.warning(request, "Produto já removido.")
        return redirect("product_list")

    try:
        name = product.name
        product.delete()
        messages.success(request, f'Produto "{name}" excluído com sucesso!')

    except ProtectedError:
        messages.error(
            request,
            "Este produto não pode ser excluído pois está sendo utilizado em um produto composto.",
        )

    return redirect("product_list")


# =========================
# Ativar/Desativar Produto
# =========================
@group_required("Supervisor")
def product_toggle(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)

    if request.method == "POST":
        try:
            product.is_active = not product.is_active
            product.save()
            action = "ativado" if product.is_active else "desativado"
            messages.success(request, f'Produto "{product.name}" {action}!')
        except Exception as e:
            messages.error(request, f"Erro ao alterar status: {str(e)}")

    return redirect("product_list")


# =========================
# Views de Modal
# =========================
@group_required("Supervisor", "Vendedor")
def product_details(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    return render(
        request,
        "catalogo/products/product_details.html",
        {"product": product},
    )


@group_required("Supervisor")
def product_edit_modal(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    categories = Category.objects.filter(is_active=True)

    return render(
        request,
        "catalogo/products/edit_modal.html",
        {
            "product": product,
            "categories": categories,
            "thickness_choices": SinglePiece.THICKNESS_CHOICES,
            "color_choices": SinglePiece.ACRYLIC_COLOR_CHOICES,
            "is_supervisor": request.user.groups.filter(name="Supervisor").exists(),
        },
    )
