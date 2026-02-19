from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction

from catalogo.models.single_piece import SinglePiece
from ..models import ProductComponent
from ..forms.composite_product import CompositeProductForm
from ..decorators import group_required


from django.db import transaction
from django.contrib import messages


@group_required("Supervisor")
def composite_product_create(request):
    if request.method == "POST":
        form = CompositeProductForm(request.POST, request.FILES)

        if form.is_valid():

            components = request.POST.getlist("components")

            # 🔴 Bloqueia se não houver componentes
            if not components:
                messages.error(
                    request, "Produto composto deve possuir pelo menos um componente."
                )
                return redirect("product_list")

            try:
                with transaction.atomic():

                    # Salva produto
                    product = form.save(commit=False)
                    product.is_sellable = True
                    product.save()

                    # Cria componentes
                    for component_id in components:
                        qty = request.POST.get(f"quantity_{component_id}", "1")

                        try:
                            qty = int(qty)
                            if qty < 1:
                                qty = 1
                        except ValueError:
                            qty = 1

                        ProductComponent.objects.create(
                            parent=product,
                            component_id=component_id,
                            quantity=qty,
                        )

                    messages.success(
                        request,
                        f'Produto composto "{product.name}" criado com sucesso '
                        f"com {len(components)} componente(s)!",
                    )

            except Exception as e:
                messages.error(request, f"Erro ao criar produto composto: {str(e)}")

        else:
            messages.error(
                request,
                "Erro ao criar produto composto. Verifique os dados do formulário.",
            )

    return redirect("product_list")


@group_required("Supervisor")
def composite_product_update(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)

    if request.method == "POST":
        form = CompositeProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()

                    messages.success(
                        request,
                        f'Produto composto "{product.name}" atualizado com sucesso.',
                    )

            except Exception as e:
                messages.error(request, f"Erro ao atualizar produto composto: {str(e)}")
        else:
            # 🔎 MOSTRAR ERROS REAIS
            print("ERROS DO FORM:", form.errors)
            messages.error(request, f"Erro no formulário: {form.errors}")

    return redirect("product_list")
