from django.db import models
from django.conf import settings
from core.models import Sequence


class Client(models.Model):
    # =========================
    # Identificação interna ERP
    # =========================
    code = models.PositiveIntegerField(
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Código"
    )

    # =========================
    # Tipo de pessoa
    # =========================
    PERSON_TYPE_CHOICES = (
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    )

    person_type = models.CharField(
        max_length=2,
        choices=PERSON_TYPE_CHOICES,
        verbose_name="Tipo"
    )

    # =========================
    # Dados principais
    # =========================
    name = models.CharField(
        max_length=255,
        verbose_name="Nome / Razão Social"
    )

    trade_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nome Fantasia"
    )

    document = models.CharField(
        max_length=18,
        unique=True,
        verbose_name="CPF / CNPJ"
    )

    state_registration = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Inscrição Estadual"
    )

    municipal_registration = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Inscrição Municipal"
    )

    # =========================
    # Contato
    # =========================
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)

    # =========================
    # Endereço
    # =========================
    zip_code = models.CharField(max_length=10, blank=True)
    street = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=20, blank=True)
    complement = models.CharField(max_length=255, blank=True)
    neighborhood = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=2, blank=True)

    # =========================
    # LGPD / Soft delete / Auditoria
    # =========================
    is_active = models.BooleanField(default=True)

    consent_at = models.DateTimeField(null=True, blank=True)
    consent_source = models.CharField(max_length=100, blank=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients_created"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients_updated"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # =========================
    # Flags futuras
    # =========================
    is_supplier = models.BooleanField(default=False)
    is_carrier = models.BooleanField(default=False)
    is_partner = models.BooleanField(default=False)

    # =========================
    # Meta
    # =========================
    class Meta:
        ordering = ["name"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["document"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = Sequence.next("CLIENT")
        super().save(*args, **kwargs)