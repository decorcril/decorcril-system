from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from ..models import SinglePiece, Category
from ..decorators import group_required

@group_required('Supervisor', 'Vendedor')
def product_list(request):
    products = SinglePiece.objects.all().order_by('sku')
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
        'is_supervisor': request.user.groups.filter(name='Supervisor').exists()
    }
    
    return render(request, 'catalogo/products/list.html', context)

@group_required('Supervisor')
def product_create(request):
    if request.method == 'POST':
        try:
            # Criar produto com todos os campos
            product = SinglePiece(
                sku=request.POST.get('sku', '').strip().upper(),
                name=request.POST.get('name', '').strip(),
                category_id=request.POST.get('category'),
                description=request.POST.get('description', ''),
                thickness_mm=request.POST.get('thickness_mm', 3),
                is_sellable=request.POST.get('is_sellable') == 'on',
                base_price=request.POST.get('base_price') or None,
                is_active=request.POST.get('is_active') == 'on',
                
                # Medidas
                height_cm=request.POST.get('height_cm') or None,
                width_cm=request.POST.get('width_cm') or None,
                length_cm=request.POST.get('length_cm') or None,
                diameter_cm=request.POST.get('diameter_cm') or None,
                depth_cm=request.POST.get('depth_cm') or None,
                curvature_cm=request.POST.get('curvature_cm') or None,
                
                # Material
                acrylic_color=request.POST.get('acrylic_color') or None,
                color_observation=request.POST.get('color_observation', ''),
                
                # Elétrica
                has_electrical_component=request.POST.get('has_electrical_component') == 'on',
                voltage=request.POST.get('voltage', ''),
                has_led=request.POST.get('has_led') == 'on',
                led_type=request.POST.get('led_type', ''),
            )
            
            # Processar foto
            if 'photo' in request.FILES:
                product.photo = request.FILES['photo']
            
            # Salvar (irá validar com clean())
            product.save()
            
            messages.success(request, f'Produto "{product.name}" criado com sucesso!')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar produto: {str(e)}')
    
    return redirect('product_list')

@group_required('Supervisor')
def product_update(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    
    if request.method == 'POST':
        try:
            # Atualizar campos básicos
            product.sku = request.POST.get('sku', '').strip().upper()
            product.name = request.POST.get('name', '').strip()
            product.category_id = request.POST.get('category')
            product.description = request.POST.get('description', '')
            product.thickness_mm = request.POST.get('thickness_mm', 3)
            product.is_sellable = request.POST.get('is_sellable') == 'on'
            
            # Preço (pode ser None se não for vendável)
            if request.POST.get('is_sellable') == 'on':
                product.base_price = request.POST.get('base_price') or None
            else:
                product.base_price = None
            
            product.is_active = request.POST.get('is_active') == 'on'
            
            # Medidas
            product.height_cm = request.POST.get('height_cm') or None
            product.width_cm = request.POST.get('width_cm') or None
            product.length_cm = request.POST.get('length_cm') or None
            product.diameter_cm = request.POST.get('diameter_cm') or None
            product.depth_cm = request.POST.get('depth_cm') or None
            product.curvature_cm = request.POST.get('curvature_cm') or None
            
            # Material
            product.acrylic_color = request.POST.get('acrylic_color') or None
            product.color_observation = request.POST.get('color_observation', '')
            
            # Elétrica
            product.has_electrical_component = request.POST.get('has_electrical_component') == 'on'
            product.voltage = request.POST.get('voltage', '')
            product.has_led = request.POST.get('has_led') == 'on'
            product.led_type = request.POST.get('led_type', '')
            
            # Processar foto se fornecida
            if 'photo' in request.FILES and request.FILES['photo']:
                product.photo = request.FILES['photo']
            
            # Salvar (irá validar com clean())
            product.save()
            
            messages.success(request, f'Produto "{product.name}" atualizado com sucesso!')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar produto: {str(e)}')
    
    return redirect('product_list')

@group_required('Supervisor')
def product_delete(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    
    if request.method == 'POST':
        try:
            product_name = product.name
            product.delete()
            messages.success(request, f'Produto "{product_name}" excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir produto: {str(e)}')
    
    return redirect('product_list')

@group_required('Supervisor')
def product_toggle(request, pk):
    product = get_object_or_404(SinglePiece, pk=pk)
    
    if request.method == 'POST':
        try:
            product.is_active = not product.is_active
            product.save()
            
            action = "ativado" if product.is_active else "desativado"
            messages.success(request, f'Produto "{product.name}" {action}!')
        except Exception as e:
            messages.error(request, f'Erro ao alterar status: {str(e)}')
    
    return redirect('product_list')

# =============================================
# NOVAS VIEWS PARA MODAIS
# =============================================

@group_required('Supervisor', 'Vendedor')
def product_details(request, pk):
    """Retorna HTML com detalhes do produto para o modal"""
    product = get_object_or_404(SinglePiece, pk=pk)
    return render(request, 'catalogo/products/product_details.html', {
        'product': product
    })

@group_required('Supervisor')
def product_edit_modal(request, pk):
    """Retorna HTML do formulário de edição para o modal"""
    product = get_object_or_404(SinglePiece, pk=pk)
    categories = Category.objects.filter(is_active=True)
    
    return render(request, 'catalogo/products/edit_modal.html', {
        'product': product,
        'categories': categories,
        'thickness_choices': SinglePiece.THICKNESS_CHOICES,
        'color_choices': SinglePiece.ACRYLIC_COLOR_CHOICES,
        'is_supervisor': request.user.groups.filter(name='Supervisor').exists()
    })