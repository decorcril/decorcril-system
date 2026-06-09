"""
Seed script para criar 300 produtos de teste.
Uso: python manage.py shell
     exec(open('seed_products.py', encoding='utf-8').read())
"""

import random
from decimal import Decimal
from catalogo.models import SinglePiece, Category

NOMES = [
    "Cubo", "Cilindro", "Base", "Tampo", "Mesa", "Bandeja",
    "Coluna", "Pedestal", "Suporte", "Painel", "Nicho", "Prateleira",
    "Porta-retrato", "Luminária", "Letreiro", "Número", "Balcão",
    "Vitrine", "Display", "Expositor", "Carrinho", "Púlpito",
]

ADJETIVOS = [
    "Redondo", "Quadrado", "Retangular", "Oval", "Hexagonal",
    "Transparente", "Espelhado", "Cristal", "Branco", "Preto",
    "Compacto", "Grande", "Médio", "Pequeno", "Mini",
    "Tradicional", "Moderno", "Clássico", "Premium", "Especial",
]

ESPESSURAS = [3, 4, 6, 8, 10]
CORES = ["CRISTAL", "BRANCO", "PRETO", "ROSA", "ESPELHADO", None, None]

categories = list(Category.objects.filter(is_active=True))
if not categories:
    print("Nenhuma categoria encontrada! Crie ao menos uma categoria primeiro.")
    exit()

print(f"Encontradas {len(categories)} categorias.")
print("Criando 300 produtos...\n")

criados = 0
erros   = 0
skus_usados = set(SinglePiece.objects.values_list("sku", flat=True))

for i in range(1, 401):
    nome      = f"{random.choice(NOMES)} {random.choice(ADJETIVOS)}"
    espessura = random.choice(ESPESSURAS)
    sku_num   = 5000 + i
    sufixo    = random.choice(["", f"-{espessura}", f"-{random.randint(1,9)}"])
    sku       = f"{sku_num}{sufixo}"

    if sku in skus_usados:
        continue
    skus_usados.add(sku)

    preco     = Decimal(str(random.randint(50, 2000)))
    categoria = random.choice(categories)
    cor       = random.choice(CORES)

    altura  = Decimal(str(random.randint(10, 100))) if random.random() > 0.3 else None
    largura = Decimal(str(random.randint(10, 100))) if random.random() > 0.3 else None

    try:
        produto = SinglePiece(
            sku          = sku,
            name         = f"{nome} {espessura}mm",
            category     = categoria,
            description  = f"Produto de teste gerado automaticamente.",
            is_sellable  = True,
            base_price   = preco,
            thickness_mm = espessura,
            acrylic_color = cor,
            height_cm    = altura,
            width_cm     = largura,
            is_active    = True,
        )
        produto.full_clean()
        produto.save()
        criados += 1

        if criados % 50 == 0:
            print(f"  {criados} produtos criados...")

        if criados >= 300:
            break

    except Exception as e:
        erros += 1

print(f"\n{criados} produtos criados com sucesso! ({erros} erros ignorados)")