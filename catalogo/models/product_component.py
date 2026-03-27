from django.db import models
from django.core.exceptions import ValidationError
from .single_piece import SinglePiece


class ProductComponent(models.Model):
    """
    Define a composição de um produto a partir de outros produtos.
    Permite composição recursiva (produto simples ou composto).
    """

    parent = models.ForeignKey(
        SinglePiece,
        on_delete=models.CASCADE,
        related_name="components",
        verbose_name="Produto composto",
    )

    component = models.ForeignKey(
        SinglePiece,
        on_delete=models.PROTECT,
        related_name="used_in_compositions",
        verbose_name="Produto componente",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade",
    )

    class Meta:
        verbose_name = "Componente de Produto"
        verbose_name_plural = "Componentes de Produto"
        unique_together = ("parent", "component")
        ordering = ["id"]

    # =========================
    # Regras de Domínio
    # =========================
    def clean(self):
        errors = {}

        # Produto não pode conter ele mesmo
        if self.parent_id and self.component_id:
            if self.parent_id == self.component_id:
                errors["component"] = "Um produto não pode conter ele mesmo."

        # Quantidade mínima
        if self.quantity < 1:
            errors["quantity"] = "A quantidade deve ser maior que zero."

        # Evitar ciclos simples (A -> B -> A)
        if self.parent_id and self.component_id:
            if self._creates_cycle():
                errors["component"] = "Essa composição cria um ciclo entre produtos."

        if errors:
            raise ValidationError(errors)

    def _creates_cycle(self):
        """
        Verifica ciclos indiretos:
        Ex: A contém B e B contém A
        """
        return ProductComponent.objects.filter(
            parent=self.component,
            component=self.parent,
        ).exists()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.component} → {self.parent}"
