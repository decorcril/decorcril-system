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
            # Mapeia label de status para valor interno (ex: "Em Produção" → "in_production")
            status_map = {label.lower(): value for value, label in Order.Status.choices}
            matched_status = next(
                (v for k, v in status_map.items() if q.lower() in k), None
            )
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
        ctx["count_total"]         = sum(status_counts.values())
        ctx["count_open"]          = status_counts.get("open", 0)
        ctx["count_in_production"] = status_counts.get("in_production", 0)
        ctx["count_picking"]       = status_counts.get("picking", 0)
        ctx["count_invoiced"]      = status_counts.get("invoiced", 0)
        ctx["count_shipped"]       = status_counts.get("shipped", 0)
        ctx["count_delivered"]     = status_counts.get("delivered", 0)
        ctx["count_canceled"]      = status_counts.get("canceled", 0)
        # Form para o modal de criação (necessário para {{ form.sale_type }})
        ctx["form"] = OrderForm()
        # Contexto de permissões
        ctx["is_supervisor"] = user.is_superuser or user.groups.filter(name="Supervisor").exists()
        ctx["is_vendedor"]   = user.groups.filter(name="Vendedor").exists()
        return ctx


# ==============================
# CRIAÇÃO DE PEDIDOS
# ==============================
class OrderCreateView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        form = OrderForm(request.POST)
        if not form.is_valid():
            print("ERROS DO FORM:", form.errors)
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
        formatted = {k: [str(e) for e in v] for k, v in errors.items()} if isinstance(errors, dict) else {"__all__": [str(errors)]}
        return JsonResponse({"success": False, "errors": formatted}, status=status)


# ==============================
# CONFIRMAÇÃO DE PEDIDO
# ==============================
class OrderConfirmView(LoginRequiredMixin, View):
    CONFIRMABLE_STATUSES = {Order.Status.OPEN, Order.Status.IN_PRODUCTION}

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        user = request.user

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
# GERENCIAMENTO DE ITENS DE PEDIDO
# ==============================
class OrderItemManager:
    """Helper para criar ou atualizar itens de pedido"""

    @staticmethod
    def parse_decimal(value, default=Decimal("0.00")):
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default

    @classmethod
    def create_or_update(cls, order, data, item_id=None):
        unit_price = cls.parse_decimal(data.get("unit_price"))
        quantity = int(data.get("quantity", 1))
        discount_percent = cls.parse_decimal(data.get("discount", "0"))
        discount = (unit_price * discount_percent / 100).quantize(Decimal("0.01")) if unit_price else Decimal("0.00")

        if item_id:
            item = get_object_or_404(OrderItem, pk=item_id)
        else:
            item = OrderItem(order=order, product_id=int(data["product_id"]))

        item.unit_price = unit_price
        item.quantity = quantity
        item.discount = discount
        item.full_clean()
        item.save()
        return item


# ==============================
# ITENS DE PEDIDO
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
        order = get_object_or_404(Order, pk=pk)
        user = request.user

        if not (user.is_superuser or order.created_by_id == user.pk):
            from django.contrib import messages
            messages.error(request, "Sem permissão para excluir este pedido.")
            return redirect("vendas:order_list")

        if order.status not in (Order.Status.OPEN,):
            from django.contrib import messages
            messages.error(request, f"Pedido {order.number} não pode ser excluído no status {order.get_status_display()}.")
            return redirect("vendas:order_list")

        order.delete()

        from django.contrib import messages
        messages.success(request, f"Pedido {order.number} excluído com sucesso.")
        return redirect("vendas:order_list")


# ==============================
# DETALHE DO PEDIDO (JSON)
# ==============================
class OrderDetailView(LoginRequiredMixin, View):
    """Retorna todos os dados de um pedido em JSON para o modal de visualização."""

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related("client", "created_by"),
            pk=pk
        )

        # Itens
        items = []
        for item in order.items.select_related("product"):
            subtotal = item.unit_price * (1 - item.discount / 100) * item.quantity if item.unit_price else 0
            p = item.product

            dims = []
            if getattr(p, "height_cm",    None): dims.append(f"Alt: {p.height_cm} cm")
            if getattr(p, "width_cm",     None): dims.append(f"Larg: {p.width_cm} cm")
            if getattr(p, "length_cm",    None): dims.append(f"Comp: {p.length_cm} cm")
            if getattr(p, "diameter_cm",  None): dims.append(f"Diâm: {p.diameter_cm} cm")
            if getattr(p, "depth_cm",     None): dims.append(f"Prof: {p.depth_cm} cm")
            if getattr(p, "curvature_cm", None): dims.append(f"Curv: {p.curvature_cm} cm")

            items.append({
                "name":       p.name,
                "sku":        p.sku or "",
                "quantity":   item.quantity,
                "unit_price": str(item.unit_price),
                "discount":   str(item.discount),
                "subtotal":   f"{subtotal:.2f}",
                "thickness":  p.get_thickness_mm_display() if getattr(p, "thickness_mm", None) else "",
                "color":      p.get_acrylic_color_display() if getattr(p, "acrylic_color", None) else "",
                "color_obs":  getattr(p, "color_observation", "") or "",
                "dimensions": " · ".join(dims),
                "voltage":    p.get_voltage_display() if getattr(p, "voltage", None) else "",
                "led":        p.get_led_type_display() if getattr(p, "has_led", None) and p.has_led else "",
            })

        # Pagamentos
        from vendas.models.payment import Payment
        payments = []
        for p in order.payments.select_related("created_by"):
            payments.append({
                "method_label": dict(Payment.Method.choices).get(p.method, p.method),
                "amount":       str(p.amount),
                "transaction":  p.transaction or "",
                "paid_at":      tz.localtime(p.paid_at).strftime("%d/%m/%Y %H:%M"),
                "created_by":   p.created_by.get_full_name() or p.created_by.username,
            })

        # Cliente
        c = order.client
        address = ", ".join(filter(None, [
            getattr(c, "street", ""), getattr(c, "number", ""),
            getattr(c, "neighborhood", ""), getattr(c, "city", ""), getattr(c, "state", "")
        ]))

        status_colors = {
            "open":          "bg-primary",
            "in_production": "bg-success",
            "picking":       "bg-info text-dark",
            "invoiced":      "bg-secondary",
            "shipped":       "bg-dark",
            "delivered":     "bg-success",
            "canceled":      "bg-danger",
        }

        return JsonResponse({
            "number":               order.number,
            "status":               order.status,
            "status_label":         order.get_status_display(),
            "status_color":         status_colors.get(order.status, "bg-light text-dark"),
            "created_at":           tz.localtime(order.created_at).strftime("%d/%m/%Y %H:%M"),
            "created_by":           order.created_by.get_full_name() or order.created_by.username,
            "sale_type":            order.get_sale_type_display() if order.sale_type else "—",
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
            "client": {
                "name":     c.name,
                "document": getattr(c, "document", "") or "—",
                "type":     c.get_person_type_display() if hasattr(c, "get_person_type_display") else "—",
                "phone":    getattr(c, "phone", "") or "—",
                "email":    getattr(c, "email", "") or "—",
                "address":  address or "—",
            },
            "items":    items,
            "payments": payments,
        })

