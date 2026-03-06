from django.db import models
from django.db import transaction


class Sequence(models.Model):
    """
    Controle de sequências ERP (CLIENT, ORDER, PRODUCT, etc.)
    """

    key = models.CharField(max_length=30, unique=True, verbose_name="Chave")

    last_value = models.PositiveBigIntegerField(default=0, verbose_name="Último valor")

    prefix = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Prefixo"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sequência"
        verbose_name_plural = "Sequências"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} ({self.last_value})"

    # =========================
    # Geração segura
    # =========================
    @classmethod
    def next(cls, key: str) -> int:
        """
        Retorna o próximo número da sequência com lock transacional
        """
        with transaction.atomic():
            seq, created = cls.objects.select_for_update().get_or_create(
                key=key, defaults={"last_value": 1000}  # <- valor inicial
            )
            seq.last_value += 1
            seq.save(update_fields=["last_value"])
            return seq.last_value

    @classmethod
    def next_formatted(cls, key: str) -> str:
        """
        Retorna número formatado com prefixo
        Ex: 000123 ou CLI-000123
        """
        with transaction.atomic():
            seq, created = cls.objects.select_for_update().get_or_create(
                key=key, defaults={"last_value": 1000}  # <- valor inicial
            )
            seq.last_value += 1
            seq.save(update_fields=["last_value"])

            number = str(seq.last_value).zfill(6)
            if seq.prefix:
                return f"{seq.prefix}-{number}"
            return number
