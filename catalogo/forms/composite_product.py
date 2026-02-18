from django import forms
from decimal import Decimal, InvalidOperation
from ..models import SinglePiece
import re


class CompositeProductForm(forms.ModelForm):
    """
    O campo base_price pode receber:
    - 2000,00
    - 2.000,00
    - 2000.00
    - R$ 2.000,00
    O backend normaliza tudo para Decimal corretamente.
    """

    base_price = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = SinglePiece
        fields = [
            "sku",
            "name",
            "category",
            "photo",
            "description",
            "base_price",
            "is_active",
        ]

        widgets = {
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    def clean_base_price(self):
        raw_value = self.cleaned_data.get("base_price")

        if not raw_value:
            raise forms.ValidationError("Produto composto precisa de preço.")

        # Remove espaços
        raw_value = str(raw_value).strip()

        # Remove qualquer coisa que não seja número, vírgula ou ponto
        raw_value = re.sub(r"[^\d,\.]", "", raw_value)

        if not raw_value:
            raise forms.ValidationError("Informe um número válido.")

        # Se tiver vírgula, assume formato brasileiro
        if "," in raw_value:
            normalized = raw_value.replace(".", "").replace(",", ".")
        else:
            normalized = raw_value

        try:
            value = Decimal(normalized)
        except (InvalidOperation, TypeError):
            raise forms.ValidationError("Informe um número válido.")

        if value < 0:
            raise forms.ValidationError("O preço não pode ser negativo.")

        return value
