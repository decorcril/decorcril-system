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

        if not _is_supervisor(user):
            qs = qs.filter(created_by=user)

        q = self.request.GET.get("q", "").strip()
        if q:
            status_map = {label.lower(): value for value, label in Order.Status.choices}
            matched_status = next((v for k, v in status_map.items() if q.lower() in k), None)
            status_filter = Q(status=matched_status) if matched_status else Q()
            qs = qs.filter(
                Q(client__name__icontains=q)    |
                Q(number__icontains=q)           |
                Q(customer_order__icontains=q)   |
                status_filter
            )
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user = self.request.user
        qs   = Order.objects if _is_supervisor(user) else Order.objects.filter(created_by=user)

        counts = {
            item["status"]: item["total"]
            for item in qs.values("status").annotate(total=Count("id"))
        }

        ctx.update({
            "count_total":         sum(counts.values()),
            "count_open":          counts.get("open", 0),
            "count_in_production": counts.get("in_production", 0),
            "count_picking":       counts.get("picking", 0),
            "count_invoiced":      counts.get("invoiced", 0),
            "count_shipped":       counts.get("shipped", 0),
            "count_delivered":     counts.get("delivered", 0),
            "count_canceled":      counts.get("canceled", 0),
            "form":                OrderForm(),
            "is_supervisor":       _is_supervisor(user),
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
            return _json_error(form.errors)

        try:
            items = json.loads(request.POST.get("items_json", "[]"))
        except (ValueError, TypeError):
            return _json_error({"items": ["Itens inválidos."]})

        if not items:
            return _json_error({"items": ["Adicione ao menos um produto."]})

        try:
            with transaction.atomic():
                form.instance.created_by = request.user
                order = form.save()
                for item_data in items:
                    OrderItemManager.create_or_update(order, item_data)
        except Exception as e:
            return _json_error({"__all__": [str(e)]})

        return JsonResponse({"success": True, "order_id": order.id, "order_number": order.number})


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
        return JsonResponse({
            "success":      True,
            "new_status":   order.status,
            "status_label": order.get_status_display(),
        })


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
# ATUALIZAÇÃO DE PEDIDO (JSON)
# ==============================
class OrderUpdateView(LoginRequiredMixin, View):
    EDITABLE_STATUSES = {Order.Status.OPEN, Order.Status.IN_PRODUCTION}

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        if order.created_by_id != request.user.pk and not request.user.is_superuser:
            return JsonResponse({"success": False, "error": "Sem permissão para editar este pedido."}, status=403)

        if order.status not in self.EDITABLE_STATUSES:
            return JsonResponse({"success": False, "error": "Pedido não pode ser editado neste status."}, status=400)

        p = request.POST
        order.sale_type            = p.get("sale_type",            order.sale_type)
        order.contact              = p.get("contact",              order.contact)
        order.customer_order       = p.get("customer_order",       order.customer_order)
        order.payment_terms        = p.get("payment_terms",        order.payment_terms)
        order.carrier              = p.get("carrier",              order.carrier)
        order.freight              = _parse_decimal(p.get("freight"),              "0")
        order.down_payment_percent = _parse_decimal(p.get("down_payment_percent"), "0")
        order.notes                = p.get("notes",                order.notes)
        order.internal_notes       = p.get("internal_notes",       order.internal_notes)

        order.save(update_fields=[
            "sale_type", "contact", "customer_order", "payment_terms",
            "carrier", "freight", "down_payment_percent",
            "notes", "internal_notes", "updated_at",
        ])
        order.sync_payment_status()
        return JsonResponse({"success": True})


# ==============================
# DETALHE DO PEDIDO (JSON)
# ==============================
class OrderDetailView(LoginRequiredMixin, View):

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
            "client":               _serialize_client(order.client),
            "items":                _serialize_items(order),
            "payments":             _serialize_payments(order, Payment),
        })


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
# GERENCIAMENTO DE ITENS
# ==============================
class OrderItemManager:

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
        if not unit_price or not percent:
            return Decimal("0.00")
        return (unit_price * percent / Decimal("100")).quantize(Decimal("0.01"))

    @classmethod
    def discount_to_percent(cls, unit_price: Decimal, discount_value: Decimal) -> Decimal:
        if not unit_price or not discount_value:
            return Decimal("0.00")
        return (discount_value / unit_price * Decimal("100")).quantize(Decimal("0.01"))

    @classmethod
    def create_or_update(cls, order, data, item_id=None) -> OrderItem:
        unit_price       = cls.parse_decimal(data.get("unit_price"))
        quantity         = int(data.get("quantity") or 1)
        discount_percent = cls.parse_decimal(data.get("discount"))
        discount_value   = cls.calculate_discount(unit_price, discount_percent)

        product_id = data.get("product_id")

        if item_id:
            item = get_object_or_404(OrderItem, pk=item_id)
        else:
            if not product_id:
                raise ValueError("product_id é obrigatório.")
            item = OrderItem(order=order)
            item.product_id = int(product_id)

        item.unit_price = unit_price
        item.quantity   = quantity
        item.discount   = discount_value
        item.full_clean()
        item.save()
        return item


# ==============================
# HELPERS PRIVADOS
# ==============================

def _is_supervisor(user) -> bool:
    return user.is_superuser or user.groups.filter(name="Supervisor").exists()


def _parse_decimal(value, default="0") -> Decimal:
    try:
        return Decimal(str(value or default).replace(",", ".").strip())
    except Exception:
        return Decimal(default)


def _json_error(errors, status=400):
    if isinstance(errors, dict):
        formatted = {k: [str(e) for e in v] for k, v in errors.items()}
    else:
        formatted = {"__all__": [str(errors)]}
    return JsonResponse({"success": False, "errors": formatted}, status=status)


def _serialize_client(c) -> dict:
    address = ", ".join(filter(None, [
        getattr(c, "street",       ""),
        getattr(c, "number",       ""),
        getattr(c, "neighborhood", ""),
        getattr(c, "city",         ""),
        getattr(c, "state",        ""),
    ]))
    return {
        "name":     c.name,
        "document": getattr(c, "document", "") or "—",
        "type":     c.get_person_type_display() if hasattr(c, "get_person_type_display") else "—",
        "phone":    getattr(c, "phone",  "") or "—",
        "email":    getattr(c, "email",  "") or "—",
        "address":  address or "—",
    }


def _serialize_items(order) -> list:
    items = []

    for item in order.items.select_related("product").prefetch_related(
        "product__components__component"
    ):
        p = item.product
        if not p:
            continue

        # ── financeiro ────────────────────────────────────────
        subtotal     = (item.unit_price - item.discount) * item.quantity if item.unit_price else Decimal("0.00")
        discount_pct = OrderItemManager.discount_to_percent(item.unit_price, item.discount)

        # ── dimensões ─────────────────────────────────────────
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

        # ── espessura ─────────────────────────────────────────
        if p.is_composite:
            thicknesses = sorted(set(
                comp.component.get_thickness_mm_display()
                for comp in p.components.all()
                if getattr(comp.component, "thickness_mm", None)
            ))
            thickness = ", ".join(thicknesses) if thicknesses else p.get_thickness_mm_display()
        else:
            thickness = p.get_thickness_mm_display() if getattr(p, "thickness_mm", None) else ""

        # ── componentes (para exibição no modal) ──────────────
        components = []
        if p.is_composite:
            for comp in p.components.all():
                components.append({
                    "name":     comp.component.name,
                    "sku":      comp.component.sku or "",
                    "quantity": comp.quantity,
                })

        items.append({
            "id":         item.pk,
            "name":       p.name,
            "sku":        p.sku or "",
            "quantity":   item.quantity,
            "unit_price": str(item.unit_price),
            "discount":   str(discount_pct),
            "subtotal":   f"{subtotal:.2f}",
            "components": components,
            "thickness":  thickness,
            "color":      p.get_acrylic_color_display() if getattr(p, "acrylic_color", None) else "",
            "color_obs":  getattr(p, "color_observation", "") or "",
            "dimensions": " · ".join(dims),
            "voltage":    p.get_voltage_display() if getattr(p, "voltage", None) else "",
            "led":        p.get_led_type_display() if getattr(p, "has_led", None) and p.has_led else "",
        })

    return items


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

class OrderCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        # Status que não podem ser cancelados
        if order.status in (Order.Status.DELIVERED, Order.Status.CANCELED):
            return JsonResponse({
                'success': False,
                'error': f'Pedido com status "{order.get_status_display()}" não pode ser cancelado.'
            })

        order.status = Order.Status.CANCELED
        order.save(update_fields=['status', 'updated_at'])

        return JsonResponse({
            'success': True,
            'status_label': order.get_status_display(),
        })