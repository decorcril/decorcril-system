from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View

from vendas.models.order import Order
from vendas.models.payment import Payment


# ==============================
# PAGAMENTOS DO PEDIDO
# ==============================
class PaymentListView(LoginRequiredMixin, View):
    """Retorna os pagamentos de um pedido em JSON."""

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        data = []
        for p in order.payments.select_related("created_by"):
            data.append({
                "id":           p.id,
                "method":       p.method,
                "method_label": dict(Payment.Method.choices).get(p.method, p.method),
                "amount":       str(p.amount),
                "transaction":  p.transaction or "",
                "notes":        p.notes or "",
                "paid_at":      timezone.localtime(p.paid_at).strftime("%d/%m/%Y %H:%M"),
                "created_by":   p.created_by.get_full_name() or p.created_by.username,
            })
        return JsonResponse({
            "payments":           data,
            "total_paid":         str(order.total_paid),
            "total_amount":       str(order.total_amount),
            "remaining":          str(order.remaining),
            "down_payment_value": str(order.down_payment_value),
            "payment_terms":      order.payment_terms or "",
        })

class PaymentCreateView(LoginRequiredMixin, View):
    """Registra um novo pagamento para um pedido."""

    def post(self, request, pk):
        # ── Permissão ─────────────────────────────────────────
        if not (request.user.is_superuser or request.user.groups.filter(
            name__in=["Supervisor", "Financeiro"]
        ).exists()):
            return JsonResponse({"success": False, "error": "Sem permissão para registrar pagamentos."}, status=403)

        order = get_object_or_404(Order, pk=pk)

        method      = request.POST.get("method", "").strip()
        amount_raw  = request.POST.get("amount", "0").strip()
        transaction = request.POST.get("transaction", "").strip() or None
        notes       = request.POST.get("notes", "").strip()

        if method not in dict(Payment.Method.choices):
            return JsonResponse({"success": False, "error": "Forma de pagamento inválida."}, status=400)

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError
        except Exception:
            return JsonResponse({"success": False, "error": "Valor inválido."}, status=400)

        payment = Payment(
            order=order,
            method=method,
            amount=amount,
            transaction=transaction,
            notes=notes,
            created_by=request.user,
        )

        try:
            payment.full_clean()
            payment.save()
        except DjangoValidationError as e:
            errors = {k: list(v) for k, v in e.message_dict.items()}
            return JsonResponse({"success": False, "errors": errors}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        return JsonResponse({
            "success":      True,
            "total_paid":   str(order.total_paid),
            "remaining":    str(order.remaining),
            "new_status":   order.status,
            "status_label": order.get_status_display(),
        })


class PaymentDeleteView(LoginRequiredMixin, View):
    """Remove um pagamento (apenas supervisor ou criador)."""

    def post(self, request, payment_pk):
        payment = get_object_or_404(Payment, pk=payment_pk)
        user = request.user

        if not (user.is_superuser or payment.created_by_id == user.pk):
            return JsonResponse({"success": False, "error": "Sem permissão."}, status=403)

        order = payment.order
        payment.delete()
        order.sync_payment_status()

        return JsonResponse({
            "success":      True,
            "total_paid":   str(order.total_paid),
            "remaining":    str(order.remaining),
            "new_status":   order.status,
            "status_label": order.get_status_display(),
        })