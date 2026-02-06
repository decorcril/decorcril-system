from django import forms
from ..models import SinglePiece


class SinglePieceForm(forms.ModelForm):
    class Meta:
        model = SinglePiece
        fields = [
            # Identificação
            "sku",
            "name",
            "photo",
            "category",
            "description",

            # Comercial
            "is_sellable",
            "base_price",

            # Medidas
            "thickness_mm",
            "height_cm",
            "width_cm",
            "length_cm",
            "diameter_cm",
            "depth_cm",
            "curvature_cm",

            # Material
            "acrylic_color",
            "color_observation",

            # Elétrica
            "has_electrical_component",
            "voltage",
            "has_led",
            "led_type",

            # Controle
            "is_active",
        ]

        widgets = {
            # =========================
            # Identificação
            # =========================
            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "EX: 001 ou 001-ABC",
                    "oninput": "this.value=this.value.toUpperCase()",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nome completo do produto",
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descrição detalhada do produto...",
                }
            ),

            # =========================
            # Comercial
            # =========================
            "is_sellable": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "base_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),

            # =========================
            # Medidas
            # =========================
            "thickness_mm": forms.Select(attrs={"class": "form-select"}),
            "height_cm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "width_cm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "length_cm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "diameter_cm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "depth_cm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "curvature_cm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),

            # =========================
            # Material
            # =========================
            "acrylic_color": forms.Select(attrs={"class": "form-select"}),
            "color_observation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex: Transparente fosco, colorido personalizado...",
                }
            ),

            # =========================
            # Elétrica
            # =========================
            "has_electrical_component": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "voltage": forms.Select(attrs={"class": "form-select"}),
            "has_led": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "led_type": forms.Select(attrs={"class": "form-select"}),

            # =========================
            # Controle
            # =========================
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        labels = {
            "sku": "SKU*",
            "name": "Nome do Produto*",
            "photo": "Foto do Produto",
            "category": "Categoria*",
            "description": "Descrição",
            "is_sellable": "Produto vendável?",
            "base_price": "Preço Base (R$)",
            "thickness_mm": "Espessura do Acrílico*",
            "height_cm": "Altura (cm)",
            "width_cm": "Largura (cm)",
            "length_cm": "Comprimento (cm)",
            "diameter_cm": "Diâmetro (cm)",
            "depth_cm": "Profundidade (cm)",
            "curvature_cm": "Curvatura (cm)",
            "acrylic_color": "Cor do Acrílico",
            "color_observation": "Observação de Cor",
            "has_electrical_component": "Possui Componente Elétrico?",
            "voltage": "Tensão",
            "has_led": "Possui LED?",
            "led_type": "Tipo de LED",
            "is_active": "Ativo",
        }

        help_texts = {
            "sku": "Código único do produto. Ex: 001, 002-ABC",
            "base_price": "Obrigatório se o produto for vendável",
            "thickness_mm": "Espessura da chapa de acrílico",
            "photo": "Imagem ilustrativa do produto (opcional)",
        }

    # =========================
    # Validações customizadas
    # =========================
    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip().upper()
        qs = SinglePiece.objects.filter(sku=sku)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Já existe um produto com este SKU.")
        return sku

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean(self):
        cleaned_data = super().clean()
        is_sellable = cleaned_data.get("is_sellable")
        base_price = cleaned_data.get("base_price")
        has_electrical = cleaned_data.get("has_electrical_component")
        voltage = cleaned_data.get("voltage")
        has_led = cleaned_data.get("has_led")
        led_type = cleaned_data.get("led_type")

        # Validação: Preço obrigatório se vendável
        if is_sellable and not base_price:
            self.add_error(
                "base_price",
                "Preço base é obrigatório se o produto for vendável."
            )

        # Validação: Se não vendável, limpar preço
        if not is_sellable:
            cleaned_data["base_price"] = None

        # Validação: Pelo menos uma medida deve ser preenchida
        medidas = [
            cleaned_data.get("height_cm"),
            cleaned_data.get("width_cm"),
            cleaned_data.get("length_cm"),
            cleaned_data.get("diameter_cm"),
            cleaned_data.get("depth_cm"),
            cleaned_data.get("curvature_cm"),
        ]
        
        if not any(medidas):
            self.add_error(
                None,
                "Pelo menos uma medida deve ser preenchida (altura, largura, comprimento, diâmetro, profundidade ou curvatura)."
            )

        # Validação: Se não tem componente elétrico, limpar campos relacionados
        if not has_electrical:
            cleaned_data["voltage"] = ""
            cleaned_data["has_led"] = False
            cleaned_data["led_type"] = ""

        # Validação: Se não tem LED, limpar tipo de LED
        if not has_led:
            cleaned_data["led_type"] = ""

        # Validação: Se tem LED, deve ter tipo de LED
        if has_led and not led_type:
            self.add_error(
                "led_type",
                "Tipo de LED é obrigatório quando o produto possui LED."
            )

        return cleaned_data