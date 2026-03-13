from django.db import models
from django.core.exceptions import ValidationError
from .single_piece import SinglePiece


class Kit(models.Model):
    """
    Define um Kit que pode conter produtos simples e produtos compostos.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome do Kit"
    )

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Preço base",
    )

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

    # Produto simples
    product = models.ForeignKey(
        SinglePiece,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="used_in_kits",
        verbose_name="Produto simples",
    )

    # Produto composto
    composed_product = models.ForeignKey(
        SinglePiece,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="used_in_kits_as_composed",
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
        unique_together = (
            ("kit", "product"),
            ("kit", "composed_product"),
        )

    # ==========================================================
    # Helper central para acessar o produto real
    # ==========================================================

    @property
    def item(self):
        """
        Retorna o produto do componente independentemente
        de ser simples ou composto.
        """
        return self.product or self.composed_product

    # ==========================================================
    # Helpers de medidas
    # ==========================================================

    @property
    def measurements(self):
        """
        Retorna as medidas formatadas do produto.
        """
        if self.item:
            return self.item.get_measurements_display()
        return "Sem medidas"

    @property
    def thickness(self):
        if self.item:
            return self.item.thickness_mm
        return None

    # ==========================================================
    # Regras de domínio
    # ==========================================================

    def clean(self):
        errors = {}

        # Deve escolher um tipo de produto
        if not self.product and not self.composed_product:
            errors["product"] = "Escolha um produto simples ou composto."

        # Não pode escolher ambos
        if self.product and self.composed_product:
            errors["product"] = (
                "Não é possível escolher produto simples e composto ao mesmo tempo."
            )

        # Produto composto precisa ser realmente composto
        if self.composed_product and not self.composed_product.is_composite:
            errors["composed_product"] = (
                "O produto selecionado não é um produto composto."
            )

        # Produto simples não pode ser composto
        if self.product and self.product.is_composite:
            errors["product"] = (
                "O produto selecionado é composto. Use o campo 'Produto composto'."
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
        item = self.item
        return f"{self.quantity}x {item} → {self.kit}"