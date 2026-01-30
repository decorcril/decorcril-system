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

    # Adicione este campo na seção "Identidade" (logo após description):
    photo = models.ImageField(
        upload_to="products/single_pieces/",
        blank=True,
        null=True,
        verbose_name="Foto do produto",
    )

# Atualize a lista de fields no Meta do formulário depois
    name = models.CharField(
        max_length=150,
        verbose_name="Nome",
    )

    category = models.ForeignKey(
        'Category',
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
        choices=THICKNESS_CHOICES,
        verbose_name="Espessura (mm)",
        default=3
    )

    # Dimensões (todas opcionais)
    height_cm = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Altura (cm)"
    )
    width_cm = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Largura (cm)"
    )
    length_cm = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Comprimento (cm)"
    )
    diameter_cm = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Diâmetro (cm)"
    )
    depth_cm = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Profundidade (cm)"
    )
    curvature_cm = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Curvatura (cm)"
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
        ("BIVOLT", "Bivolt"),
    ]

    voltage = models.CharField(
        max_length=10,
        choices=VOLTAGE_CHOICES,
        blank=True,
        verbose_name="Tensão",
    )

    has_led = models.BooleanField(
        default=False,
        verbose_name="Possui LED?",
    )

    LED_TYPE_CHOICES = [
        ("", "Selecione..."),
        ("QUENTE", "Quente"),
        ("FRIO", "Frio"),
    ]

    led_type = models.CharField(
        max_length=10,
        choices=LED_TYPE_CHOICES,
        blank=True,
        verbose_name="Tipo de LED",
    )

    # =========================
    # Controle
    # =========================
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produto Acrílico"
        verbose_name_plural = "Produtos Acrílicos"
        ordering = ['sku']

    # =========================
    # Regras de Domínio
    # =========================
    def clean(self):
        errors = {}

        # Normalização
        if self.name:
            self.name = self.name.strip().title()

        if self.sku:
            self.sku = self.sku.strip().upper()
            if not re.match(r"^\d+(-[A-Z0-9]+)?$", self.sku):
                errors["sku"] = "SKU inválido. Use formato: 123 ou 123-ABC"

        # Comercial
        if self.is_sellable and self.base_price is None:
            errors["base_price"] = "Produto vendável precisa de preço."

        if not self.is_sellable and self.base_price is not None:
            errors["base_price"] = "Peça não vendável não deve ter preço."

        # Elétrica
        if self.has_electrical_component and not self.voltage:
            errors["voltage"] = "Informe a tensão."

        if self.has_led and not self.has_electrical_component:
            errors["has_led"] = "LED exige componente elétrico."

        if self.has_led and not self.led_type:
            errors["led_type"] = "Informe o tipo de LED."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def get_measurements_display(self):
        """Retorna string formatada com medidas"""
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