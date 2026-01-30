from django import forms
from ..models import SinglePiece

class SinglePieceForm(forms.ModelForm):
    class Meta:
        model = SinglePiece
        fields = [
            'sku', 'name', 'category', 'description',
            'is_sellable', 'base_price',  # Mudado de 'price' para 'base_price'
            'thickness_mm',
            'height_cm', 'width_cm', 'length_cm',
            'diameter_cm', 'depth_cm', 'curvature_cm',
            'acrylic_color', 'color_observation',
            'has_electrical_component', 'voltage',
            'has_led', 'led_type',
            'is_active'
        ]
        widgets = {
            # Identificação
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'EX: 001 ou 001-ABC',
                'oninput': 'this.value = this.value.toUpperCase()'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo do produto'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição detalhada do produto...'
            }),
            
            # Comercial
            'is_sellable': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'togglePriceField(this)'
            }),
            'base_price': forms.NumberInput(attrs={  # Mudado de 'price' para 'base_price'
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            
            # Medidas
            'thickness_mm': forms.Select(attrs={
                'class': 'form-select'
            }),
            'height_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'width_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'length_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'diameter_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'depth_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'curvature_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            
            # Material
            'acrylic_color': forms.Select(attrs={
                'class': 'form-select'
            }),
            'color_observation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Transparente fosco, Colorido personalizado...'
            }),
            
            # Elétrica
            'has_electrical_component': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'toggleElectricalFields(this)'
            }),
            'voltage': forms.Select(attrs={
                'class': 'form-select'
            }),
            'has_led': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'toggleLEDField(this)'
            }),
            'led_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            
            # Controle
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'sku': 'SKU*',
            'name': 'Nome do Produto*',
            'category': 'Categoria*',
            'description': 'Descrição',
            'is_sellable': 'É vendável?',
            'base_price': 'Preço Base (R$)',  # Mudado de 'price' para 'base_price'
            'thickness_mm': 'Espessura do Acrílico*',
            'height_cm': 'Altura (cm)',
            'width_cm': 'Largura (cm)',
            'length_cm': 'Comprimento (cm)',
            'diameter_cm': 'Diâmetro (cm)',
            'depth_cm': 'Profundidade (cm)',
            'curvature_cm': 'Curvatura (cm)',
            'acrylic_color': 'Cor do Acrílico',
            'color_observation': 'Observação de Cor',
            'has_electrical_component': 'Possui Componente Elétrico?',
            'voltage': 'Tensão',
            'has_led': 'Possui LED?',
            'led_type': 'Tipo de LED',
            'is_active': 'Ativo'
        }
        help_texts = {
            'sku': 'Código único do produto. Ex: 001, 002-ABC',
            'is_sellable': 'Se não for vendável, não aparecerá no catálogo',
            'base_price': 'Obrigatório se o produto for vendável',  # Mudado
            'thickness_mm': 'Espessura da chapa de acrílico',
        }