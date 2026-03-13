import os
from django.db import models
from django.core.exceptions import ValidationError
import re


class SinglePiece(models.Model):
    # =========================
    # Identidade
    # =========================
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="SKU (código interno)",
    )

    photo = models.ImageField(
        upload_to="products/single_pieces/",
        blank=True,
        null=True,
        verbose_name="Foto do produto",
    )

    name = models.CharField(
        max_length=150,
        verbose_name="Nome",
    )

    category = models.ForeignKey(
        "Category",
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Categoria",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Descrição",
    )

    # =========================
    # Comercial
    # =========================
    is_sellable = models.BooleanField(
        default=True,
        verbose_name="É vendável?",
        help_text="Se marcado, aparece no catálogo e exige preço",
    )

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Preço base",
    )

    # =========================
    # Medidas
    # =========================
    THICKNESS_CHOICES = [
        (2, "2 mm"),
        (3, "3 mm"),
        (4, "4 mm"),
        (6, "6 mm"),
        (8, "8 mm"),
        (10, "10 mm"),
        (12, "12 mm"),
    ]

    thickness_mm = models.PositiveSmallIntegerField(
        choices=THICKNESS_CHOICES, verbose_name="Espessura (mm)", default=3
    )

    height_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Altura (cm)",
    )
    width_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Largura (cm)",
    )
    length_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Comprimento (cm)",
    )
    diameter_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Diâmetro (cm)",
    )
    depth_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Profundidade (cm)",
    )
    curvature_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Curvatura (cm)",
    )

    # =========================
    # Material
    # =========================
    ACRYLIC_COLOR_CHOICES = [
        ("CRISTAL", "Cristal"),
        ("BRANCO", "Branco"),
        ("PRETO", "Preto"),
        ("ROSA", "Rosa"),
        ("ROSA_BEBE", "Rosa Bebê"),
        ("AZUL", "Azul"),
        ("AZUL_BEBE", "Azul Bebê"),
        ("ESPELHADO", "Espelhado"),
        ("ESPELHADO_TRANSPARENTE", "Espelhado Transparente"),
        ("COLORIDO", "Colorido"),
    ]

    acrylic_color = models.CharField(
        max_length=30,
        choices=ACRYLIC_COLOR_CHOICES,
        blank=True,
        null=True,
        verbose_name="Cor do acrílico",
    )

    color_observation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Observação de cor",
    )

    # =========================
    # Elétrica
    # =========================
    has_electrical_component = models.BooleanField(
        default=False,
        verbose_name="Possui componente elétrico?",
    )

    VOLTAGE_CHOICES = [
        ("", "Selecione..."),
        ("127", "127V"),
        ("220", "220V"),
        ("BIVOLT", "Bivolt"),
    ]

    voltage = models.CharField(
        max_length=10,
        choices=VOLTAGE_CHOICES,
        blank=True,
        verbose_name="Tensão",
    )

    has_led = models.BooleanField(default=False, verbose_name="Possui LED?")

    LED_TYPE_CHOICES = [
        ("", "Selecione..."),
        ("QUENTE", "Quente"),
        ("FRIO", "Frio"),
    ]

    led_type = models.CharField(
        max_length=10, choices=LED_TYPE_CHOICES, blank=True, verbose_name="Tipo de LED"
    )

    # =========================
    # Controle
    # =========================
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_kit = models.BooleanField(
        default=False,
        verbose_name="É kit?",
        help_text="Identifica se este produto é um kit",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # =========================
    # Regras de Domínio
    # =========================
    def clean(self):
        errors = {}
        if self.name:
            self.name = self.name.strip()

        if self.sku:
            self.sku = self.sku.strip().upper()
            if not re.match(r"^\d+(-[A-Z0-9]+)?$", self.sku):
                errors["sku"] = "SKU inválido. Use formato: 123 ou 123-ABC"

        if self.is_sellable and self.base_price is None:
            errors["base_price"] = "Produto vendável precisa de preço."

        if not self.is_sellable and self.base_price is not None:
            errors["base_price"] = "Peça não vendável não deve ter preço."

        if self.has_electrical_component and not self.voltage:
            errors["voltage"] = "Informe a tensão."

        if self.has_led and not self.has_electrical_component:
            errors["has_led"] = "LED exige componente elétrico."

        if self.has_led and not self.led_type:
            errors["led_type"] = "Informe o tipo de LED."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Remove a imagem antiga se estiver sendo substituída
        if self.pk:
            old_instance = SinglePiece.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.photo and old_instance.photo != self.photo:
                if os.path.isfile(old_instance.photo.path):
                    os.remove(old_instance.photo.path)

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Remove a imagem ao deletar o produto
        if self.photo and os.path.isfile(self.photo.path):
            os.remove(self.photo.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_measurements_display(self):
        measurements = []
        if self.height_cm:
            measurements.append(f"Altura: {self.height_cm}cm")
        if self.width_cm:
            measurements.append(f"Largura: {self.width_cm}cm")
        if self.length_cm:
            measurements.append(f"Comprimento: {self.length_cm}cm")
        if self.diameter_cm:
            measurements.append(f"Diâmetro: {self.diameter_cm}cm")
        if self.depth_cm:
            measurements.append(f"Profundidade: {self.depth_cm}cm")
        if self.curvature_cm:
            measurements.append(f"Curvatura: {self.curvature_cm}cm")
        return ", ".join(measurements) if measurements else "Sem medidas"

    @property
    def is_composite(self):
        return not self.is_kit and self.components.exists()

    @property
    def numeric_fields(self):
        """Retorna campos numéricos sempre com ponto decimal (seguro para data-* attributes)."""
        def fmt(v):
            return f"{v:.2f}" if v is not None else ""

        return {
            "base_price":   fmt(self.base_price),
            "height_cm":    fmt(self.height_cm),
            "width_cm":     fmt(self.width_cm),
            "length_cm":    fmt(self.length_cm),
            "diameter_cm":  fmt(self.diameter_cm),
            "depth_cm":     fmt(self.depth_cm),
            "curvature_cm": fmt(self.curvature_cm),
        }
