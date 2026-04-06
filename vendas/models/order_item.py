from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Sum

from catalogo.models.single_piece import SinglePiece
from catalogo.models.kit_component import Kit
from vendas.models.order import Order

TWO = Decimal("0.01")


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Pedido",
    )
    product = models.ForeignKey(
        SinglePiece,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Produto",
    )
    kit = models.ForeignKey(
        Kit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Kit",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Valor unitário"
    )

    class Meta:
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"
        ordering = ["id"]

    # ---------------------------------------------------------
    # Validação
    # ---------------------------------------------------------

    def clean(self):
        errors = {}

        if not self.product and not self.kit:
            errors["product"] = "Escolha um produto ou um kit."
        if self.product and self.kit:
            errors["product"] = "Não é possível escolher produto e kit ao mesmo tempo."
        if self.product and not self.product.is_sellable:
            errors["product"] = "Este produto não está disponível para venda."
        if self.unit_price is None or self.unit_price < 0:
            errors["unit_price"] = "Preço unitário inválido."
        if self.quantity < 1:
            errors["quantity"] = "Quantidade mínima é 1."

        if errors:
            raise ValidationError(errors)

    # ---------------------------------------------------------
    # Financeiro
    # ---------------------------------------------------------

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(TWO, rounding=ROUND_HALF_UP)

    # ---------------------------------------------------------
    # Expansão estrutural
    # ---------------------------------------------------------

    def get_real_products(self):
        result = []
        if self.product:
            result.extend(self._expand_product(self.product, self.quantity))
        elif self.kit:
            for component in self.kit.components.all():
                result.extend(self._expand_product(component.item, component.quantity * self.quantity))
        return result

    def _expand_product(self, product, quantity):
        if product.is_composite:
            return [(comp.component, comp.quantity * quantity) for comp in product.components.all()]
        return [(product, quantity)]

    # ---------------------------------------------------------
    # Persistência
    # ---------------------------------------------------------

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self._sync_order_totals()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        self._sync_order_totals(order)

    # ---------------------------------------------------------
    # Totais do pedido
    # ---------------------------------------------------------

    def _sync_order_totals(self, order=None):
        order = order or self.order

        agg = order.items.aggregate(
            total_products=Sum(F("unit_price") * F("quantity")),
        )

        total_products = Decimal(str(agg["total_products"] or 0)).quantize(TWO)

        order.total_products = total_products
        order.total_amount = (
            total_products - order.total_discount + order.freight
        ).quantize(TWO)

        order.save(update_fields=["total_products", "total_amount"])

        if hasattr(order, "sync_payment_status"):
            order.sync_payment_status()

    # ---------------------------------------------------------
    # Representação
    # ---------------------------------------------------------

    def __str__(self):
        name = self.product.name if self.product else (self.kit.name if self.kit else "Item")
        return f"{self.quantity}x {name} → {self.order}"