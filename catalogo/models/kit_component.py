from django.db import models
from django.core.exceptions import ValidationError
from .single_piece import SinglePiece
from .product_component import ProductComponent


class Kit(models.Model):
    """
    Define um Kit que pode conter produtos simples e produtos compostos.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Nome do Kit")

    class Meta:
        verbose_name = "Kit"
        verbose_name_plural = "Kits"
        ordering = ["id"]

    def __str__(self):
        return self.name


class KitComponent(models.Model):
    """
    Composição de um Kit a partir de produtos simples e produtos compostos.
    """

    kit = models.ForeignKey(
        Kit,
        on_delete=models.CASCADE,
        related_name="components",
        verbose_name="Kit",
    )

    # Referencia um produto simples
    product = models.ForeignKey(
        SinglePiece,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="used_in_kits",
        verbose_name="Produto simples",
    )

    # Referencia um produto composto
    composed_product = models.ForeignKey(
        ProductComponent,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="used_in_kits",
        verbose_name="Produto composto",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade",
    )

    class Meta:
        verbose_name = "Componente de Kit"
        verbose_name_plural = "Componentes de Kit"
        ordering = ["id"]
        # Garante que não repita o mesmo produto simples ou composto no mesmo kit
        unique_together = (
            ("kit", "product"),
            ("kit", "composed_product"),
        )

    # =========================
    # Regras de domínio
    # =========================
    def clean(self):
        errors = {}

        # Um componente deve ser ou produto simples ou produto composto
        if not self.product and not self.composed_product:
            errors["product"] = "Escolha um produto simples ou composto."
        if self.product and self.composed_product:
            errors["product"] = (
                "Não é possível escolher produto simples e composto ao mesmo tempo."
            )

        # Quantidade mínima
        if self.quantity < 1:
            errors["quantity"] = "A quantidade deve ser maior que zero."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        item = self.product or self.composed_product
        return f"{self.quantity}x {item} → {self.kit}"
