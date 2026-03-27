import re
from django import template

register = template.Library()


@register.filter
def format_document(value):
    """Formata CPF (11 dígitos) ou CNPJ (14 dígitos)."""
    if not value:
        return value
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return value


@register.filter
def format_phone(value):
    """Formata telefone fixo (10 dígitos) ou celular/WhatsApp (11 dígitos)."""
    if not value:
        return value
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    return value


@register.filter
def format_cep(value):
    """Formata CEP (8 dígitos) → 00000-000."""
    if not value:
        return value
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return value
