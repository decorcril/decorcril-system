import os

from django.db import models
from django.conf import settings
from vendas.models.order import Order


class Invoice(models.Model):
    order      = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice', verbose_name='Pedido')
    file       = models.FileField('Arquivo da NF', upload_to='invoices/%Y/%m/')
    number     = models.CharField('Número da NF', max_length=50)
    issued_at  = models.DateField('Data de emissão')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Registrado por')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        order = self.order
        if order.status == Order.Status.IN_PRODUCTION:
            order.status = Order.Status.PICKING
            order.save(update_fields=['status', 'updated_at'])

    def delete(self, *args, **kwargs):
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'NF {self.number} — Pedido {self.order.number}'

    class Meta:
        verbose_name        = 'Nota Fiscal'
        verbose_name_plural = 'Notas Fiscais'