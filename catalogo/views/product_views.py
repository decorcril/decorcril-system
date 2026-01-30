from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import SinglePiece, Category
from ..forms import SinglePieceForm
from ..decorators import group_required

@group_required('Supervisor', 'Vendedor')
def product_list(request):
    products = SinglePiece.objects.all().order_by('sku')
    categories = Category.objects.filter(is_active=True)
    form = SinglePieceForm()
    
    context = {
        'products': products,
        'categories': categories,
        'form': form,
        'is_supervisor': request.user.groups.filter(name='Supervisor').exists()
    }
    
    return render(request, 'catalogo/products/list.html', context)

@group_required('Supervisor')
def product_create(request):
    if request.method == 'POST':
        form = SinglePieceForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Produto "{product.name}" criado com sucesso!')
            return redirect('product_list')
        else:
            # Se o formulário for inválido, mostra os erros
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('product_list')

@group_required('Supervisor')
def product_update(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    
    if request.method == 'POST':
        form = SinglePieceForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Produto "{product.name}" atualizado!')
            return redirect('product_list')
    
    return redirect('product_list')

@group_required('Supervisor')
def product_delete(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Produto "{product_name}" excluído!')
        return redirect('product_list')
    
    return redirect('product_list')

@group_required('Supervisor')
def product_toggle(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    product.is_active = not product.is_active
    product.save()
    
    action = "ativado" if product.is_active else "desativado"
    messages.success(request, f'Produto "{product.name}" {action}!')
    
    return redirect('product_list')