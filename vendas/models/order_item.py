from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Sum
from catalogo.models.single_piece import SinglePiece
from vendas.models.order import Order

TWO = Decimal("0.01")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Pedido")
    product = models.ForeignKey(SinglePiece, on_delete=models.PROTECT, verbose_name="Produto")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor unitário")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="Desconto por unidade (R$)")

    class Meta:
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"
        unique_together = ("order", "product")

    def clean(self):
        errors = {}
        if self.product and not self.product.is_sellable:
            errors["product"] = "Este produto não está disponível para venda."
        if self.unit_price is None or self.unit_price < 0:
            errors["unit_price"] = "Preço unitário inválido (deve ser >= 0)."
        if self.quantity < 1:
            errors["quantity"] = "Quantidade mínima é 1."
        if self.discount < 0 or (self.unit_price is not None and self.discount > self.unit_price):
            errors["discount"] = "Desconto inválido."
        if errors:
            raise ValidationError(errors)

    @property
    def subtotal(self) -> Decimal:
        return ((self.unit_price - self.discount) * self.quantity).quantize(TWO, rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self._sync_order_totals()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        self._sync_order_totals(order=order)

    def _sync_order_totals(self, order=None):
        order = order or self.order
        agg = order.items.aggregate(
            total_products=Sum(F("unit_price") * F("quantity")),
            total_discount=Sum(F("discount") * F("quantity")),
        )
        total_products = Decimal(str(agg["total_products"] or 0)).quantize(TWO)
        total_discount = Decimal(str(agg["total_discount"] or 0)).quantize(TWO)
        order.total_products = total_products
        order.total_discount = total_discount
        order.total_amount = (total_products - total_discount + order.freight).quantize(TWO)
        order.save(update_fields=["total_products", "total_discount", "total_amount"])
        if hasattr(order, "sync_payment_status"):
            order.sync_payment_status()

    def __str__(self):
        return f"{self.quantity}x {self.product} → {self.order}"