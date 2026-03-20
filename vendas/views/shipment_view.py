import os

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from vendas.models.order import Order
from vendas.models.shipment import Shipment


class ShipmentCreateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        user  = request.user

        if not (user.is_superuser or user.groups.filter(name__in=["Supervisor", "Financeiro"]).exists()):
            return JsonResponse({"success": False, "error": "Sem permissão para registrar envio."}, status=403)

        if order.status != Order.Status.PICKING:
            return JsonResponse({
                "success": False,
                "error": f'Pedido está em "{order.get_status_display()}" — envio só pode ser registrado em pedidos Em Separação.'
            }, status=400)

        if hasattr(order, 'shipment'):
            return JsonResponse({"success": False, "error": "Este pedido já possui um envio registrado."}, status=400)

        file    = request.FILES.get("file")
        tracking = request.POST.get("tracking", "").strip()
        carrier  = request.POST.get("carrier",  "").strip()

        if not file:
            return JsonResponse({"success": False, "error": "Comprovante de envio é obrigatório."}, status=400)

        try:
            shipment = Shipment(
                order      = order,
                file       = file,
                tracking   = tracking,
                carrier    = carrier,
                created_by = user,
            )
            shipment.full_clean()
            shipment.save()  # muda status para SHIPPED automaticamente
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        return JsonResponse({
            "success":      True,
            "status_label": order.get_status_display(),
            "shipment": {
                "tracking":  shipment.tracking  or "—",
                "carrier":   shipment.carrier   or "—",
                "file_url":  shipment.file.url,
                "created_at": shipment.created_at.strftime("%d/%m/%Y %H:%M"),
            }
        })


class ShipmentDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        user  = request.user

        if not (user.is_superuser or user.groups.filter(name__in=["Supervisor", "Financeiro"]).exists()):
            return JsonResponse({"success": False, "error": "Sem permissão para remover envio."}, status=403)

        if not hasattr(order, 'shipment'):
            return JsonResponse({"success": False, "error": "Este pedido não possui envio registrado."}, status=404)

        order.shipment.delete()

        order.status = Order.Status.PICKING
        order.save(update_fields=["status", "updated_at"])

        return JsonResponse({
            "success":      True,
            "status_label": order.get_status_display(),
        })