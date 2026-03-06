from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from vendas.models.order import Order

TWO = Decimal("0.01")


class Payment(models.Model):

    class Method(models.TextChoices):
        PIX      = "pix",      "PIX"
        DEBIT    = "debit",    "Cartão de Débito"
        CREDIT   = "credit",   "Cartão de Crédito"
        BOLETO   = "boleto",   "Boleto"
        CASH     = "cash",     "Dinheiro"
        TRANSFER = "transfer", "Transferência"

    order       = models.ForeignKey(Order, related_name="payments", on_delete=models.CASCADE, verbose_name="Pedido")
    method      = models.CharField("Forma de pagamento", max_length=20, choices=Method.choices)
    amount      = models.DecimalField("Valor pago", max_digits=12, decimal_places=2)
    transaction = models.CharField("Número de transação", max_length=100, blank=True, unique=True, null=True,
                                   help_text="Código PIX, NSU do cartão, número do boleto etc.")
    notes       = models.TextField("Observações", blank=True)
    paid_at     = models.DateTimeField("Data do pagamento", auto_now_add=True)
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Registrado por", on_delete=models.PROTECT)

    def clean(self):
        if self.transaction:
            qs = Payment.objects.filter(transaction=self.transaction)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    "transaction": f"O número de transação '{self.transaction}' já foi utilizado em outro pagamento."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.order.sync_payment_status()

    def __str__(self):
        return f"{self.get_method_display()} — R$ {self.amount} ({self.order.number})"

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"
        ordering = ["-paid_at"]