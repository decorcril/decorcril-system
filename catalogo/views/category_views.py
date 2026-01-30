from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms
from ..models import Category
from ..decorators import group_required

# Form inline (temporário)
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

@group_required('Supervisor', 'Vendedor')
def category_list(request):
    categories = Category.objects.all().order_by('name')
    form = CategoryForm()
    
    context = {
        'categories': categories,
        'form': form,
        'is_supervisor': request.user.groups.filter(name='Supervisor').exists()
    }
    
    return render(request, 'catalogo/categories/list.html', context)

@group_required('Supervisor')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Categoria "{category.name}" criada com sucesso!')
        else:
            messages.error(request, 'Erro ao criar categoria. Verifique os dados.')
    
    return redirect('category_list')

@group_required('Supervisor')
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Categoria "{category.name}" atualizada!')
    
    return redirect('category_list')

@group_required('Supervisor')
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Categoria "{category_name}" excluída!')
    
    return redirect('category_list')

@group_required('Supervisor')
def category_toggle(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save()
    
    action = "ativada" if category.is_active else "desativada"
    messages.success(request, f'Categoria "{category.name}" {action}!')
    
    return redirect('category_list')