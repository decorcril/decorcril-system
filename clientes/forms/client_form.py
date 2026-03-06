import re
from django import forms
from ..models.client import Client


# =========================
# Helpers de normalização
# =========================
def only_digits(value):
    return re.sub(r"\D", "", value or "")


# =========================
# Validação CPF
# =========================
def validate_cpf(cpf):
    cpf = only_digits(cpf)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for i in range(9, 11):
        value = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
        digit = ((value * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False

    return True


# =========================
# Validação CNPJ
# =========================
def validate_cnpj(cnpj):
    cnpj = only_digits(cnpj)

    if len(cnpj) != 14:
        return False

    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6] + weights_1

    def calc_digit(numbers, weights):
        total = sum(int(n) * w for n, w in zip(numbers, weights))
        digit = 11 - (total % 11)
        return str(digit if digit < 10 else 0)

    digit1 = calc_digit(cnpj[:12], weights_1)
    digit2 = calc_digit(cnpj[:12] + digit1, weights_2)

    return cnpj[-2:] == digit1 + digit2


# =========================
# Form Base
# =========================
class ClientForm(forms.ModelForm):

    class Meta:
        model = Client
        exclude = (
            "code",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "anonymized_at",
        )

    # =========================
    # Limpeza geral
    # =========================
    def clean_document(self):
        person_type = self.cleaned_data.get("person_type")
        document = only_digits(self.cleaned_data.get("document"))

        if person_type == "PF":
            if not validate_cpf(document):
                raise forms.ValidationError("CPF inválido")

        elif person_type == "PJ":
            if not validate_cnpj(document):
                raise forms.ValidationError("CNPJ inválido")

        return document

    def clean_phone(self):
        return only_digits(self.cleaned_data.get("phone"))

    def clean_whatsapp(self):
        return only_digits(self.cleaned_data.get("whatsapp"))

    def clean_zip_code(self):
        return only_digits(self.cleaned_data.get("zip_code"))

    # =========================
    # Regras PF / PJ
    # =========================
    def clean(self):
        cleaned = super().clean()

        person_type = cleaned.get("person_type")
        trade_name = cleaned.get("trade_name")

        if person_type == "PF" and trade_name:
            self.add_error(
                "trade_name", "Nome fantasia não se aplica para Pessoa Física"
            )

        return cleaned


# =========================
# Form Supervisor (completo)
# =========================
class ClientFormSupervisor(ClientForm):
    class Meta(ClientForm.Meta):
        pass


# =========================
# Form Vendedor (restrito)
# =========================
class ClientFormVendedor(ClientForm):
    class Meta(ClientForm.Meta):
        exclude = ClientForm.Meta.exclude + (
            "document",
            "status",
        )
