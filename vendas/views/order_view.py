import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone as tz
from django.views import View
from django.views.generic import ListView

from vendas.forms.order_forms import OrderForm
from vendas.models.order import Order
from vendas.models.order_item import OrderItem


# ==============================
# LISTAGEM DE PEDIDOS
# ==============================
class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "vendas/orders/list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related("client", "created_by", "assigned_to")
        if not (user.is_superuser or user.groups.filter(name="Supervisor").exists()):
            qs = qs.filter(created_by=user)

        q = self.request.GET.get("q", "").strip()
        if q:
            status_map = {label.lower(): value for value, label in Order.Status.choices}
            matched_status = next((v for k, v in status_map.items() if q.lower() in k), None)
            status_filter = Q(status=matched_status) if matched_status else Q()
            qs = qs.filter(
                Q(client__name__icontains=q) |
                Q(number__icontains=q)        |
                Q(customer_order__icontains=q)|
                status_filter
            )
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        qs = Order.objects
        if not (user.is_superuser or user.groups.filter(name="Supervisor").exists()):
            qs = qs.filter(created_by=user)

        counts = qs.values("status").annotate(total=Count("id"))
        status_counts = {item["status"]: item["total"] for item in counts}

        ctx.update({
            "count_total":         sum(status_counts.values()),
            "count_open":          status_counts.get("open", 0),
            "count_in_production": status_counts.get("in_production", 0),
            "count_picking":       status_counts.get("picking", 0),
            "count_invoiced":      status_counts.get("invoiced", 0),
            "count_shipped":       status_counts.get("shipped", 0),
            "count_delivered":     status_counts.get("delivered", 0),
            "count_canceled":      status_counts.get("canceled", 0),
            "form":                OrderForm(),
            "is_supervisor":       user.is_superuser or user.groups.filter(name="Supervisor").exists(),
            "is_vendedor":         user.groups.filter(name="Vendedor").exists(),
        })
        return ctx


# ==============================
# CRIAÇÃO DE PEDIDOS
# ==============================
class OrderCreateView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        form = OrderForm(request.POST)
        if not form.is_valid():
            return self._json_error(form.errors)

        try:
            items = json.loads(request.POST.get("items_json", "[]"))
        except (ValueError, TypeError):
            return self._json_error({"items": ["Itens inválidos."]})

        if not items:
            return self._json_error({"items": ["Adicione ao menos um produto."]})

        try:
            with transaction.atomic():
                form.instance.created_by = request.user
                order = form.save()
                for item_data in items:
                    OrderItemManager.create_or_update(order, item_data)
        except Exception as e:
            return self._json_error({"__all__": [str(e)]})

        return JsonResponse({"success": True, "order_id": order.id, "order_number": order.number})

    @staticmethod
    def _json_error(errors, status=400):
        if isinstance(errors, dict):
            formatted = {k: [str(e) for e in v] for k, v in errors.items()}
        else:
            formatted = {"__all__": [str(errors)]}
        return JsonResponse({"success": False, "errors": formatted}, status=status)


# ==============================
# CONFIRMAÇÃO DE PEDIDO
# ==============================
class OrderConfirmView(LoginRequiredMixin, View):
    CONFIRMABLE_STATUSES = {Order.Status.OPEN, Order.Status.IN_PRODUCTION}

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        user  = request.user

        if not (user.is_superuser or order.created_by_id == user.pk):
            return JsonResponse({"success": False, "error": "Sem permissão para confirmar."}, status=403)

        if order.status not in self.CONFIRMABLE_STATUSES:
            return JsonResponse({
                "success": False,
                "error": f"Pedido não pode ser confirmado no status {order.get_status_display()}."
            }, status=400)

        order.status = Order.Status.IN_PRODUCTION
        order.save(update_fields=["status", "updated_at"])
        return JsonResponse({"success": True, "new_status": order.status, "status_label": order.get_status_display()})


# ==============================
# GERENCIAMENTO DE ITENS
# ==============================
class OrderItemManager:
    """Gerencia criação e atualização de itens de pedido."""

    @staticmethod
    def parse_decimal(value, default=Decimal("0.00")) -> Decimal:
        if value is None:
            return default
        try:
            return Decimal(str(value).replace("%", "").replace(",", ".").strip())
        except (InvalidOperation, ValueError, TypeError):
            return default

    @classmethod
    def calculate_discount(cls, unit_price: Decimal, percent: Decimal) -> Decimal:
        """Percentual → valor monetário do desconto (salvo no banco)."""
        if not unit_price or not percent:
            return Decimal("0.00")
        return (unit_price * percent / Decimal("100")).quantize(Decimal("0.01"))

    @classmethod
    def discount_to_percent(cls, unit_price: Decimal, discount_value: Decimal) -> Decimal:
        """Valor monetário do desconto → percentual (para exibição)."""
        if not unit_price or not discount_value:
            return Decimal("0.00")
        return (discount_value / unit_price * Decimal("100")).quantize(Decimal("0.01"))

    @classmethod
    def create_or_update(cls, order, data, item_id=None) -> OrderItem:
        unit_price       = cls.parse_decimal(data.get("unit_price"))
        quantity         = int(data.get("quantity") or 1)
        discount_percent = cls.parse_decimal(data.get("discount"))
        discount_value   = cls.calculate_discount(unit_price, discount_percent)

        if item_id:
            item = get_object_or_404(OrderItem, pk=item_id)
        else:
            item = OrderItem(order=order, product_id=int(data["product_id"]))

        item.unit_price = unit_price
        item.quantity   = quantity
        item.discount   = discount_value  # salvo em reais no banco

        item.full_clean()
        item.save()
        return item


# ==============================
# ITENS DE PEDIDO (CRUD)
# ==============================
class OrderItemListView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        items = list(order.items.select_related("product").values(
            "id", "product__name", "product__sku", "quantity", "unit_price", "discount"
        ))
        return JsonResponse({"items": items})


class OrderItemCreateView(LoginRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        try:
            OrderItemManager.create_or_update(order, request.POST)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)


class OrderItemUpdateView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        try:
            OrderItemManager.create_or_update(None, request.POST, item_id=item_id)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)


class OrderItemDeleteView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(OrderItem, pk=item_id)
        try:
            item.delete()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)


# ==============================
# DELEÇÃO DE PEDIDO
# ==============================
class OrderDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        from django.contrib import messages
        order = get_object_or_404(Order, pk=pk)
        user  = request.user

        if not (user.is_superuser or order.created_by_id == user.pk):
            messages.error(request, "Sem permissão para excluir este pedido.")
            return redirect("vendas:order_list")

        if order.status not in (Order.Status.OPEN,):
            messages.error(request, f"Pedido {order.number} não pode ser excluído no status {order.get_status_display()}.")
            return redirect("vendas:order_list")

        order.delete()
        messages.success(request, f"Pedido {order.number} excluído com sucesso.")
        return redirect("vendas:order_list")


# ==============================
# DETALHE DO PEDIDO (JSON)
# ==============================
class OrderDetailView(LoginRequiredMixin, View):
    """Retorna todos os dados de um pedido em JSON para o modal de visualização."""

    STATUS_COLORS = {
        "open":          "bg-primary",
        "in_production": "bg-success",
        "picking":       "bg-info text-dark",
        "invoiced":      "bg-secondary",
        "shipped":       "bg-dark",
        "delivered":     "bg-success",
        "canceled":      "bg-danger",
    }

    def get(self, request, pk):
        from vendas.models.payment import Payment

        order = get_object_or_404(
            Order.objects.select_related("client", "created_by"), pk=pk
        )

        return JsonResponse({
            "number":               order.number,
            "status":               order.status,
            "status_label":         order.get_status_display(),
            "status_color":         self.STATUS_COLORS.get(order.status, "bg-light text-dark"),
            "created_at":           tz.localtime(order.created_at).strftime("%d/%m/%Y %H:%M"),
            "created_by":           order.created_by.get_full_name() or order.created_by.username,
            "sale_type":            order.get_sale_type_display() if order.sale_type else "—",
            "sale_type_raw":        order.sale_type or "",
            "contact":              order.contact or "—",
            "customer_order":       order.customer_order or "—",
            "payment_terms":        order.payment_terms or "—",
            "carrier":              order.carrier or "—",
            "freight":              str(order.freight),
            "down_payment_percent": str(order.down_payment_percent),
            "down_payment_value":   str(order.down_payment_value),
            "notes":                order.notes or "—",
            "internal_notes":       order.internal_notes or "—",
            "total_amount":         str(order.total_amount),
            "total_paid":           str(order.total_paid),
            "remaining":            str(order.remaining),
            "client":               self._serialize_client(order.client),
            "items":                self._serialize_items(order),
            "payments":             self._serialize_payments(order, Payment),
        })

    # ── helpers privados ──────────────────────────────────────

    @staticmethod
    def _serialize_client(c) -> dict:
        address = ", ".join(filter(None, [
            getattr(c, "street", ""),
            getattr(c, "number", ""),
            getattr(c, "neighborhood", ""),
            getattr(c, "city", ""),
            getattr(c, "state", ""),
        ]))
        return {
            "name":     c.name,
            "document": getattr(c, "document", "") or "—",
            "type":     c.get_person_type_display() if hasattr(c, "get_person_type_display") else "—",
            "phone":    getattr(c, "phone", "") or "—",
            "email":    getattr(c, "email", "") or "—",
            "address":  address or "—",
        }

    @staticmethod
    def _serialize_items(order) -> list:
        items = []
        for item in order.items.select_related("product"):
            p            = item.product
            subtotal     = (item.unit_price - item.discount) * item.quantity if item.unit_price else Decimal("0.00")
            discount_pct = OrderItemManager.discount_to_percent(item.unit_price, item.discount)

            dims = []
            for attr, label in [
                ("height_cm",    "Alt"),
                ("width_cm",     "Larg"),
                ("length_cm",    "Comp"),
                ("diameter_cm",  "Diâm"),
                ("depth_cm",     "Prof"),
                ("curvature_cm", "Curv"),
            ]:
                val = getattr(p, attr, None)
                if val:
                    dims.append(f"{label}: {val} cm")

            items.append({
                "name":       p.name,
                "sku":        p.sku or "",
                "quantity":   item.quantity,
                "unit_price": str(item.unit_price),
                "discount":   str(discount_pct),  # exibido como %
                "subtotal":   f"{subtotal:.2f}",
                "thickness":  p.get_thickness_mm_display() if getattr(p, "thickness_mm", None) else "",
                "color":      p.get_acrylic_color_display() if getattr(p, "acrylic_color", None) else "",
                "color_obs":  getattr(p, "color_observation", "") or "",
                "dimensions": " · ".join(dims),
                "voltage":    p.get_voltage_display() if getattr(p, "voltage", None) else "",
                "led":        p.get_led_type_display() if getattr(p, "has_led", None) and p.has_led else "",
            })
        return items

    @staticmethod
    def _serialize_payments(order, Payment) -> list:
        method_map = dict(Payment.Method.choices)
        return [
            {
                "method_label": method_map.get(p.method, p.method),
                "amount":       str(p.amount),
                "transaction":  p.transaction or "",
                "paid_at":      tz.localtime(p.paid_at).strftime("%d/%m/%Y %H:%M"),
                "created_by":   p.created_by.get_full_name() or p.created_by.username,
            }
            for p in order.payments.select_related("created_by")
        ]