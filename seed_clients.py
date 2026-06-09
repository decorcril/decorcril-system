"""
Seed script para criar 200 clientes de teste.
Uso: python manage.py shell
     exec(open('seed_clients.py', encoding='utf-8').read())
"""

import random
from clientes.models import Client

NOMES_PF = [
    "Ana Silva", "Carlos Santos", "Maria Oliveira", "João Costa", "Fernanda Lima",
    "Roberto Alves", "Patricia Souza", "Lucas Ferreira", "Juliana Rocha", "Marcos Pereira",
    "Amanda Martins", "Felipe Rodrigues", "Camila Nascimento", "Bruno Carvalho", "Larissa Gomes",
    "Eduardo Barbosa", "Vanessa Ribeiro", "Thiago Araujo", "Gabriela Melo", "Rafael Dias",
    "Beatriz Castro", "Diego Moreira", "Leticia Pinto", "Henrique Correia", "Isabela Nunes",
    "Gustavo Mendes", "Natalia Vieira", "Leonardo Freitas", "Priscila Cardoso", "Vinicius Teixeira",
]

NOMES_PJ = [
    "Decor Arte LTDA", "Festas & Cia ME", "Buffet Elegance LTDA", "Eventos Premium ME",
    "Arte em Acrílico LTDA", "Festas do Futuro ME", "Decorações Silva LTDA",
    "Party Design ME", "Buffet Requinte LTDA", "Celebrações & Arte ME",
    "Espaço Fest LTDA", "Décor Total ME", "Festas Criativas LTDA", "Arte Fest ME",
    "Design de Festas LTDA", "Buffet Sonhos ME", "Eventos & Decor LTDA",
    "Festa Completa ME", "Decoração VIP LTDA", "Buffet Glamour ME",
]

CIDADES = [
    ("Sao Paulo", "SP"), ("Campinas", "SP"), ("Santos", "SP"), ("Guarulhos", "SP"),
    ("Mogi das Cruzes", "SP"), ("Suzano", "SP"), ("Ribeirao Preto", "SP"),
    ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"), ("Curitiba", "PR"),
    ("Porto Alegre", "RS"), ("Salvador", "BA"), ("Fortaleza", "CE"),
    ("Recife", "PE"), ("Brasilia", "DF"), ("Goiania", "GO"), ("Manaus", "AM"),
]

BAIRROS = [
    "Centro", "Jardim America", "Vila Nova", "Parque Industrial",
    "Jardim Paulista", "Vila Maria", "Bela Vista", "Moema",
]

PAGAMENTO = [
    "30 dias", "A vista", "50% ant + 50% retirada", "30/60 dias", "Cartao"
]

cpfs_usados = set(Client.objects.values_list("document", flat=True))

print("Criando 200 clientes de teste...\n")

criados = 0
erros   = 0

for i in range(1, 300):
    is_pf = random.random() > 0.4
    cidade, estado = random.choice(CIDADES)

    if is_pf:
        nome = random.choice(NOMES_PF) + f" {i}"
        # CPF fictício único
        doc_num = f"{random.randint(100,999)}{random.randint(100,999)}{random.randint(100,999)}{random.randint(10,99)}"
        document = doc_num[:11]
        person_type = "PF"
    else:
        nome = random.choice(NOMES_PJ) + f" {i}"
        doc_num = f"{random.randint(10,99)}{random.randint(100,999)}{random.randint(100,999)}{random.randint(1000,9999)}{random.randint(10,99)}"
        document = doc_num[:14]
        person_type = "PJ"

    if document in cpfs_usados:
        continue
    cpfs_usados.add(document)

    phone    = f"11{random.randint(90000,99999)}{random.randint(1000,9999)}"
    whatsapp = f"11{random.randint(90000,99999)}{random.randint(1000,9999)}"
    zip_code = f"{random.randint(10000,99999)}{random.randint(100,999)}"

    try:
        client = Client(
            person_type  = person_type,
            name         = nome,
            document     = document,
            email        = f"contato{i}@teste.com.br",
            phone        = phone,
            whatsapp     = whatsapp,
            zip_code     = zip_code,
            street       = f"Rua Teste {i}",
            number       = str(random.randint(1, 999)),
            neighborhood = random.choice(BAIRROS),
            city         = cidade,
            state        = estado,
            is_active    = True,
        )
        client.save()
        criados += 1

        if criados % 50 == 0:
            print(f"  {criados} clientes criados...")

        if criados >= 200:
            break

    except Exception as e:
        erros += 1

print(f"\n{criados} clientes criados com sucesso! ({erros} erros ignorados)")