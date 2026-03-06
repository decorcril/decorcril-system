from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from clientes.models import Client
from catalogo.models.single_piece import SinglePiece


class BaseAutocompleteView(LoginRequiredMixin, View):
    """Classe base para autocompletes com filtro mínimo de caracteres."""

    min_chars = 2
    max_results = 10

    def get_query(self, request):
        return request.GET.get("q", "").strip()

    def too_short(self, q):
        return len(q) < self.min_chars


# ==============================
# CLIENTE
# ==============================
class ClientAutocompleteView(BaseAutocompleteView):
    max_results = 10

    def get(self, request):
        q = self.get_query(request)
        if self.too_short(q):
            return JsonResponse([], safe=False)

        clients = (
            Client.objects.filter(is_active=True)
            .filter(Q(name__icontains=q) | Q(document__icontains=q) | Q(code__icontains=q))
            .values(
                "id", "code", "name", "document", "person_type",
                "phone", "email", "street", "number", "neighborhood", "city", "state"
            )[: self.max_results]
        )

        results = []
        for c in clients:
            address = ", ".join(filter(None, [
                c["street"], c["number"], c["neighborhood"], c["city"], c["state"]
            ]))
            results.append({
                "id": c["id"],
                "text": c["name"],
                "detail": f'{c["code"]} · {c["document"]}',
                "badge": c["person_type"],
                "phone": c.get("phone") or "",
                "email": c.get("email") or "",
                "address": address,
            })

        return JsonResponse(results, safe=False)


# ==============================
# PRODUTO
# ==============================
class ProductAutocompleteView(BaseAutocompleteView):
    max_results = 20

    def get(self, request):
        q = self.get_query(request)
        if self.too_short(q):
            return JsonResponse([], safe=False)

        products = (
            SinglePiece.objects.filter(is_active=True, is_sellable=True)
            .filter(Q(name__icontains=q) | Q(sku__icontains=q))
            .values("id", "name", "sku", "base_price", "is_kit")[: self.max_results]
        )

        results = [
            {
                "id": p["id"],
                "type": "kit" if p["is_kit"] else "product",
                "text": p["name"],
                "sku": p["sku"],
                "price": f"{p['base_price'] or 0:.2f}",
            }
            for p in products
        ]

        return JsonResponse(results, safe=False)