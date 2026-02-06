from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import SinglePiece, Category
from ..forms.product_forms import SinglePieceForm
from ..decorators import group_required


# =========================
# Listagem de Produtos
# =========================
@group_required("Supervisor", "Vendedor")
def product_list(request):
    products = SinglePiece.objects.all().order_by("sku")
    categories = Category.objects.filter(is_active=True)

    # Filtro de pesquisa
    q = request.GET.get("q", "").strip()
    if q:
        # Busca no nome, SKU e nome da categoria
        products = (
            products.filter(name__icontains=q) |
            products.filter(sku__icontains=q) |
            products.filter(category__name__icontains=q)
        )

    form = SinglePieceForm()

    context = {
        "products": products,
        "categories": categories,
        "form": form,
        "is_supervisor": request.user.groups.filter(name="Supervisor").exists(),
        "query": q,
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
            messages.success(request, f'Produto "{product.name}" atualizado com sucesso!')
        else:
            messages.error(request, "Erro ao atualizar produto. Verifique os dados.")
    return redirect("product_list")


# =========================
# Deletar Produto
# =========================
@group_required("Supervisor")
def product_delete(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    if request.method == "POST":
        try:
            name = product.name
            product.delete()
            messages.success(request, f'Produto "{name}" excluído com sucesso!')
        except Exception as e:
            messages.error(request, f"Erro ao excluir produto: {str(e)}")
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
    """Retorna HTML com detalhes do produto para o modal"""
    product = get_object_or_404(SinglePiece, pk=pk)
    return render(
        request,
        "catalogo/products/product_details.html",
        {"product": product},
    )


@group_required("Supervisor")
def product_edit_modal(request, pk):
    """Retorna HTML do formulário de edição para o modal"""
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
