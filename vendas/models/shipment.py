import os

from django.db import models
from django.conf import settings
from vendas.models.order import Order


class Shipment(models.Model):
    order      = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipment', verbose_name='Pedido')
    file       = models.FileField('Comprovante de envio', upload_to='shipments/%Y/%m/')
    tracking   = models.CharField('Código de rastreio', max_length=100, blank=True)
    carrier    = models.CharField('Transportadora', max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Registrado por')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        order = self.order
        if order.status == Order.Status.PICKING:
            order.status = Order.Status.SHIPPED
            order.save(update_fields=['status', 'updated_at'])

    def delete(self, *args, **kwargs):
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'Envio — Pedido {self.order.number}'

    class Meta:
        verbose_name        = 'Envio'
        verbose_name_plural = 'Envios'