from decimal import Decimal
from django.db import models
from django.conf import settings
from core.models import Sequence
from clientes.models import Client

TWO = Decimal("0.01")

# Tipos de venda que não exigem pagamento para entrar em produção
FREE_SALE_TYPES = {"exchange", "maintenance", "advertising"}


class Order(models.Model):
    """
    Pedido de venda completo, criado diretamente (não depende mais de Budget).
    """

    class Status(models.TextChoices):
        OPEN          = "open",          "Em aberto"
        IN_PRODUCTION = "in_production", "Em Produção"
        PICKING       = "picking",       "Em Separação"
        INVOICED      = "invoiced",      "Faturado"
        SHIPPED       = "shipped",       "Enviado"
        DELIVERED     = "delivered",     "Entregue"
        CANCELED      = "canceled",      "Cancelado"

    class SaleType(models.TextChoices):
        DIRECT      = "direct",      "Venda direta"
        EXCHANGE    = "exchange",    "Troca"
        MAINTENANCE = "maintenance", "Manutenção"
        ADVERTISING = "advertising", "Publicidade"

    # IDENTIFICAÇÃO
    number = models.CharField("Número do pedido", max_length=20, unique=True, blank=True, db_index=True)

    # RELACIONAMENTOS
    client      = models.ForeignKey(Client, verbose_name="Cliente", related_name="orders", on_delete=models.PROTECT)
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Criado por", related_name="orders_created", on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Responsável", related_name="orders_assigned", on_delete=models.PROTECT, null=True, blank=True)

    # DATAS
    created_at    = models.DateTimeField("Data de criação", auto_now_add=True)
    updated_at    = models.DateTimeField("Última atualização", auto_now=True)
    delivery_date = models.DateField("Data de entrega prevista", null=True, blank=True)

    # STATUS E TIPO
    status    = models.CharField("Status do pedido", max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    sale_type = models.CharField("Tipo de venda", max_length=20, choices=SaleType.choices, blank=True)

    # DADOS COMERCIAIS
    customer_order = models.CharField("Pedido do cliente", max_length=100, blank=True)
    payment_terms  = models.CharField("Condição de pagamento", max_length=100, blank=True)
    contact        = models.CharField("Contato", max_length=100, blank=True)
    carrier        = models.CharField("Transportadora", max_length=50, blank=True)
    freight        = models.DecimalField("Frete", max_digits=10, decimal_places=2, default=0)

    # PAGAMENTO
    down_payment_percent = models.DecimalField(
        "Entrada acordada (%)", max_digits=5, decimal_places=2,
        default=Decimal("0.00"), blank=True,
        help_text="Percentual mínimo para liberar produção (ex: 30 = 30%)"
    )

    # OBSERVAÇÕES
    notes          = models.TextField("Observações", blank=True)
    internal_notes = models.TextField("Observações internas", blank=True)

    # TOTAIS (cache)
    total_products = models.DecimalField("Total produtos",              max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField("Total desconto",              max_digits=12, decimal_places=2, default=0)
    total_taxes    = models.DecimalField("Total impostos (IPI + ICMS)", max_digits=12, decimal_places=2, default=0)
    total_amount   = models.DecimalField("Total geral",                 max_digits=12, decimal_places=2, default=0)

    # ── SAVE ─────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        if not self.pk and not self.number:
            self.number = Sequence.next_formatted("order")
        if not self.assigned_to:
            self.assigned_to = self.created_by
        super().save(*args, **kwargs)

    # ── PROPERTIES ───────────────────────────────────────────
    @property
    def is_free_sale(self) -> bool:
        """Venda sem cobrança (troca, manutenção, publicidade)."""
        return self.sale_type in FREE_SALE_TYPES

    @property
    def total_paid(self) -> Decimal:
        result = self.payments.aggregate(total=models.Sum("amount"))["total"]
        return (result or Decimal("0.00")).quantize(TWO)

    @property
    def remaining(self) -> Decimal:
        return max(Decimal("0.00"), self.total_amount - self.total_paid)

    @property
    def down_payment_value(self) -> Decimal:
        return (self.total_amount * self.down_payment_percent / 100).quantize(TWO)

    @property
    def total_amount_display(self) -> str:
        return f"{self.total_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # ── STATUS ───────────────────────────────────────────────
    def sync_payment_status(self):
        """
        Regras de transição automática de status:

        - Troca / Manutenção / Publicidade → vai direto para Em Produção
          (não exige pagamento)
        - Venda direta → Em Produção só após registrar pagamento;
          sem pagamento volta para Em aberto

        Status acima de IN_PRODUCTION (picking, invoiced, shipped,
        delivered, canceled) são gerenciados pela cobrança/logística
        e nunca são alterados aqui.
        """
        protected_statuses = {
            self.Status.PICKING,
            self.Status.INVOICED,
            self.Status.SHIPPED,
            self.Status.DELIVERED,
            self.Status.CANCELED,
        }
        if self.status in protected_statuses:
            return

        if self.is_free_sale:
            # Vendas sem cobrança entram direto em produção
            new_status = self.Status.IN_PRODUCTION
        else:
            # Venda direta: exige ao menos um pagamento
            new_status = self.Status.IN_PRODUCTION if self.payments.exists() else self.Status.OPEN

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])

    # ── META ─────────────────────────────────────────────────
    def __str__(self):
        return f"Pedido {self.number} - {self.client.name}"

    class Meta:
        verbose_name        = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["number"]),
            models.Index(fields=["status"]),
        ]