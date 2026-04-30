"""
Seed script para criar pedidos de teste.
Uso: python manage.py shell < seed_orders.py
  ou: python manage.py runscript seed_orders (com django-extensions)
"""

import random
from decimal import Decimal
from django.contrib.auth.models import User
from clientes.models import Client
from catalogo.models.single_piece import SinglePiece
from vendas.models.order import Order
from vendas.models.order_item import OrderItem

# ── Configurações ─────────────────────────────────────────────
TOTAL_PEDIDOS = 25

STATUSES = [
    "open", "open", "open",
    "in_production", "in_production",
    "picking",
    "invoiced",
    "shipped",
    "delivered",
    "canceled",
]

SALE_TYPES = [
    "direct", "direct", "direct", "direct",
    "replacement", "exchange", "maintenance", "advertising",
]

CARRIERS = [
    "Contratação Remetente - CIF",
    "Contratação Destinatário - FOB",
    "Envio pela Decorcril",
    "Retirada na Loja",
]

PAYMENT_TERMS = [
    "À vista", "30 dias", "50% ant + 50% retirada",
    "30/60 dias", "Cartão de crédito",
]

# ── Verifica pré-requisitos ───────────────────────────────────
users    = list(User.objects.filter(is_active=True))
clients  = list(Client.objects.filter(is_active=True))
products = list(SinglePiece.objects.filter(is_active=True)[:50])

if not users:
    print("❌ Nenhum usuário encontrado. Crie um superusuário primeiro.")
    exit()

if not clients:
    print("❌ Nenhum cliente encontrado. Crie clientes primeiro.")
    exit()

if not products:
    print("❌ Nenhum produto encontrado. Crie produtos primeiro.")
    exit()

print(f"✅ Encontrado: {len(users)} usuários, {len(clients)} clientes, {len(products)} produtos")
print(f"🔄 Criando {TOTAL_PEDIDOS} pedidos de teste...\n")

# ── Criação dos pedidos ───────────────────────────────────────
criados = 0

for i in range(TOTAL_PEDIDOS):
    user       = random.choice(users)
    client     = random.choice(clients)
    sale_type  = random.choice(SALE_TYPES)
    status     = random.choice(STATUSES)
    freight    = Decimal(str(random.choice([0, 0, 0, 50, 100, 150, 200])))

    try:
        order = Order(
            client             = client,
            created_by         = user,
            sale_type          = sale_type,
            status             = status,
            carrier            = random.choice(CARRIERS),
            payment_terms      = random.choice(PAYMENT_TERMS),
            contact            = f"Contato {i+1}",
            freight            = freight,
            down_payment_percent = Decimal(str(random.choice([0, 30, 50]))),
            notes              = f"Pedido de teste #{i+1}",
        )
        order.save()

        # Adiciona de 1 a 4 itens
        num_items = random.randint(1, 4)
        itens_add = random.sample(products, min(num_items, len(products)))

        for product in itens_add:
            price = product.price if hasattr(product, 'price') and product.price else Decimal(str(random.randint(50, 1000)))
            qty   = random.randint(1, 5)

            item = OrderItem(
                order      = order,
                product    = product,
                quantity   = qty,
                unit_price = price,
            )
            item.save()

        # Aplica desconto automático para vendas sem cobrança
        from vendas.models.order import FREE_SALE_TYPES
        order.refresh_from_db()
        if order.sale_type in FREE_SALE_TYPES:
            order.total_discount = order.total_products
        order.total_amount = (order.total_products - order.total_discount + order.freight)
        order.save(update_fields=["total_discount", "total_amount"])

        criados += 1
        print(f"  ✅ Pedido {order.number} — {client.name} — {order.get_status_display()}")

    except Exception as e:
        print(f"  ❌ Erro no pedido {i+1}: {e}")

print(f"\n🎉 {criados}/{TOTAL_PEDIDOS} pedidos criados com sucesso!")