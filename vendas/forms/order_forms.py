from decimal import Decimal

from django import forms
from vendas.models.order import Order
from clientes.models import Client


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "client",
            "sale_type",
            "down_payment_percent",
            "payment_terms",
            "customer_order",
            "contact",
            "carrier",
            "freight",
            "notes",
            "internal_notes",
        ]

        widgets = {
            "client": forms.Select(attrs={"class": "form-select select2", "data-placeholder": "Pesquisar cliente..."}),
            "sale_type": forms.Select(attrs={"class": "form-select"}),
            "down_payment_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}),
            "payment_terms": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 30/60 dias"}),
            "customer_order": forms.TextInput(attrs={"class": "form-control", "placeholder": "Pedido do cliente"}),
            "contact": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome do contato"}),
            "carrier": forms.TextInput(attrs={"class": "form-control", "placeholder": "Transportadora"}),
            "freight": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "internal_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

        labels = {
            "client": "Cliente",
            "sale_type": "Tipo de venda",
            "down_payment_percent": "Entrada acordada (%)",
            "payment_terms": "Condição de pagamento",
            "customer_order": "Pedido do cliente",
            "contact": "Contato",
            "carrier": "Transportadora",
            "freight": "Frete",
            "notes": "Observações",
            "internal_notes": "Observações internas",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Somente clientes ativos
        self.fields["client"].queryset = Client.objects.filter(is_active=True).order_by("name")

        # Opção padrão para tipo de venda
        self.fields["sale_type"].choices = [("", "Selecione...")] + list(Order.SaleType.choices)

        # Campos opcionais
        self.fields["freight"].required = False
        self.fields["down_payment_percent"].required = False

    def clean_freight(self):
        freight = self.cleaned_data.get("freight") or 0
        if freight < 0:
            raise forms.ValidationError("Frete não pode ser negativo.")
        return freight

    def clean_down_payment_percent(self):
        pct = self.cleaned_data.get("down_payment_percent") or Decimal("0.00")
        if pct < 0 or pct > 100:
            raise forms.ValidationError("Percentual deve ser entre 0 e 100.")
        return pct