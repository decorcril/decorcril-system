from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from vendas.models.order import Order
from vendas.models.invoice import Invoice


class InvoiceCreateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        user  = request.user

        # Apenas Financeiro ou Supervisor
        if not (user.is_superuser or user.groups.filter(name__in=["Supervisor", "Financeiro"]).exists()):
            return JsonResponse({"success": False, "error": "Sem permissão para anexar nota fiscal."}, status=403)

        # Pedido precisa estar Em Produção
        if order.status != Order.Status.IN_PRODUCTION:
            return JsonResponse({
                "success": False,
                "error": f'Pedido está em "{order.get_status_display()}" — NF só pode ser anexada em pedidos Em Produção.'
            }, status=400)

        # Já tem NF?
        if hasattr(order, 'invoice'):
            return JsonResponse({"success": False, "error": "Este pedido já possui uma nota fiscal anexada."}, status=400)

        # Valida campos
        number    = request.POST.get("number", "").strip()
        issued_at = request.POST.get("issued_at", "").strip()
        file      = request.FILES.get("file")

        if not number:
            return JsonResponse({"success": False, "error": "Número da NF é obrigatório."}, status=400)
        if not issued_at:
            return JsonResponse({"success": False, "error": "Data de emissão é obrigatória."}, status=400)
        if not file:
            return JsonResponse({"success": False, "error": "Arquivo da NF é obrigatório."}, status=400)

        try:
            invoice = Invoice(
                order      = order,
                number     = number,
                issued_at  = issued_at,
                file       = file,
                created_by = user,
            )
            invoice.full_clean()
            invoice.save()  # já muda status para PICKING automaticamente
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        return JsonResponse({
            "success":      True,
            "status_label": order.get_status_display(),
            "invoice": {
                "number":    invoice.number,
                "issued_at": invoice.issued_at.strftime("%d/%m/%Y"),
                "file_url":  invoice.file.url,
            }
        })


class InvoiceDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        user  = request.user

        if not (user.is_superuser or user.groups.filter(name__in=["Supervisor", "Financeiro"]).exists()):
            return JsonResponse({"success": False, "error": "Sem permissão para remover nota fiscal."}, status=403)

        if not hasattr(order, 'invoice'):
            return JsonResponse({"success": False, "error": "Este pedido não possui nota fiscal."}, status=404)

        order.invoice.delete()

        # Volta para Em Produção
        order.status = Order.Status.IN_PRODUCTION
        order.save(update_fields=["status", "updated_at"])

        return JsonResponse({
            "success":      True,
            "status_label": order.get_status_display(),
        })