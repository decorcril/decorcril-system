from django import forms
from ..models import Kit


class KitForm(forms.ModelForm):
    """
    Formulário para criar ou atualizar Kits.
    Segue exatamente o padrão dos forms existentes.
    """

    class Meta:
        model = Kit
        fields = [
            "name",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nome do Kit",
                }
            ),
        }
        labels = {
            "name": "Nome do Kit*",
        }
        help_texts = {
            "name": "Nome único do Kit",
        }

    # =========================
    # Validações customizadas
    # =========================
    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Kit.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Já existe um Kit com este nome.")
        return name
