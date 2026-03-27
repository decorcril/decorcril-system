from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from catalogo.models import SinglePiece, Category
from decimal import Decimal
import time


class ProductDeleteTestCase(TestCase):
    """Testes para a funcionalidade de deletar produtos"""

    def setUp(self):
        """Configuração inicial dos testes"""
        # Criar grupos
        self.supervisor_group = Group.objects.create(name="Supervisor")
        self.vendedor_group = Group.objects.create(name="Vendedor")

        # Criar usuários
        self.supervisor = User.objects.create_user(
            username="supervisor", password="test123"
        )
        self.supervisor.groups.add(self.supervisor_group)

        self.vendedor = User.objects.create_user(
            username="vendedor", password="test123"
        )
        self.vendedor.groups.add(self.vendedor_group)

        # Criar categoria
        self.category = Category.objects.create(
            name="Letras",
            description="Letras decorativas",
            is_active=True,
        )

        # Cliente HTTP
        self.client = Client()

    def create_product(self, sku, name="Produto Teste", **kwargs):
        """Helper para criar produtos"""
        defaults = {
            "name": name,
            "category": self.category,
            "thickness_mm": 3,
            "is_sellable": True,
            "base_price": Decimal("50.00"),
        }
        defaults.update(kwargs)
        return SinglePiece.objects.create(sku=sku, **defaults)

    # =========================
    # Testes de Permissão
    # =========================

    def test_delete_requires_login(self):
        """Usuário não autenticado não pode deletar"""
        product = self.create_product("001")
        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SinglePiece.objects.filter(pk=product.pk).exists())

    def test_vendedor_cannot_delete(self):
        """Vendedor não pode deletar produtos"""
        self.client.login(username="vendedor", password="test123")
        product = self.create_product("002")
        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        # Deve redirecionar ou negar acesso
        self.assertTrue(SinglePiece.objects.filter(pk=product.pk).exists())

    def test_supervisor_can_delete(self):
        """Supervisor pode deletar produtos"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("003")
        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SinglePiece.objects.filter(pk=product.pk).exists())

    # =========================
    # Testes de Funcionalidade
    # =========================

    def test_delete_existing_product(self):
        """Deletar produto existente"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("004", name="Letra A")

        initial_count = SinglePiece.objects.count()
        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(SinglePiece.objects.count(), initial_count - 1)
        self.assertFalse(SinglePiece.objects.filter(sku="004").exists())

    def test_delete_nonexistent_product(self):
        """Tentar deletar produto inexistente retorna 404"""
        self.client.login(username="supervisor", password="test123")
        response = self.client.post(reverse("product_delete", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)

    def test_delete_only_accepts_post(self):
        """DELETE só aceita método POST"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("005")

        # GET não deve deletar
        response = self.client.get(reverse("product_delete", kwargs={"pk": product.pk}))
        self.assertTrue(SinglePiece.objects.filter(pk=product.pk).exists())

    def test_delete_redirects_to_list(self):
        """Após deletar, redireciona para lista de produtos"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("006")

        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertRedirects(response, reverse("product_list"))

    def test_delete_shows_success_message(self):
        """Mostra mensagem de sucesso ao deletar"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("007", name="Produto para Deletar")

        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk}), follow=True
        )

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertIn("excluído com sucesso", str(messages[0]))
        # O nome é capitalizado pelo model (title())
        self.assertIn("Produto Para Deletar", str(messages[0]))

    # =========================
    # Testes de Edge Cases
    # =========================

    def test_delete_product_with_special_characters(self):
        """Deletar produto com caracteres especiais no nome"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("008", name="Letra Ç - Ação & Diversão")

        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SinglePiece.objects.filter(sku="008").exists())

    def test_delete_inactive_product(self):
        """Pode deletar produto inativo"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("009", is_active=False)

        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SinglePiece.objects.filter(sku="009").exists())

    def test_delete_non_sellable_product(self):
        """Pode deletar produto não vendável"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("010", is_sellable=False, base_price=None)

        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SinglePiece.objects.filter(sku="010").exists())

    def test_delete_product_with_all_fields(self):
        """Deletar produto com todos os campos preenchidos"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product(
            "011",
            name="Letra Completa",
            description="Descrição completa",
            thickness_mm=6,
            height_cm=Decimal("30.00"),
            width_cm=Decimal("20.00"),
            acrylic_color="ROSA",
            has_electrical_component=True,
            voltage="BIVOLT",
            has_led=True,
            led_type="QUENTE",
        )

        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SinglePiece.objects.filter(sku="011").exists())

    # =========================
    # Teste de Performance
    # =========================

    def test_create_and_delete_300_products(self):
        """Criar 300 produtos e testar deleção em massa"""
        self.client.login(username="supervisor", password="test123")

        print("\n" + "=" * 60)
        print("TESTE DE PERFORMANCE - 300 PRODUTOS")
        print("=" * 60)

        # Criar 300 produtos
        print("\n1. Criando 300 produtos...")
        start_time = time.time()

        products = []
        for i in range(1, 301):
            product = SinglePiece(
                sku=f"PERF-{i:03d}",
                name=f"Produto Performance {i}",
                category=self.category,
                thickness_mm=3,
                is_sellable=i % 2 == 0,  # Metade vendável, metade não
                base_price=Decimal("50.00") if i % 2 == 0 else None,
                height_cm=Decimal("10.00") if i % 3 == 0 else None,
                width_cm=Decimal("15.00") if i % 3 == 0 else None,
                acrylic_color="CRISTAL" if i % 4 == 0 else None,
                has_electrical_component=i % 5 == 0,
                voltage="BIVOLT" if i % 5 == 0 else "",
                is_active=i % 10 != 0,  # 10% inativos
            )
            products.append(product)

        SinglePiece.objects.bulk_create(products)
        creation_time = time.time() - start_time

        total_products = SinglePiece.objects.count()
        print(f"   ✓ {total_products} produtos criados em {creation_time:.2f}s")
        print(f"   ✓ Taxa: {total_products/creation_time:.0f} produtos/segundo")

        # Verificar distribuição
        vendaveis = SinglePiece.objects.filter(is_sellable=True).count()
        com_medidas = SinglePiece.objects.filter(height_cm__isnull=False).count()
        com_eletrica = SinglePiece.objects.filter(has_electrical_component=True).count()
        inativos = SinglePiece.objects.filter(is_active=False).count()

        print(f"\n   Distribuição:")
        print(f"   - Vendáveis: {vendaveis}")
        print(f"   - Com medidas: {com_medidas}")
        print(f"   - Com componente elétrico: {com_eletrica}")
        print(f"   - Inativos: {inativos}")

        # Testar deleção individual
        print("\n2. Testando deleção individual...")
        product_to_delete = SinglePiece.objects.filter(sku="PERF-050").first()
        start_time = time.time()

        response = self.client.post(
            reverse("product_delete", kwargs={"pk": product_to_delete.pk})
        )
        delete_time = time.time() - start_time

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SinglePiece.objects.filter(sku="PERF-050").exists())
        print(f"   ✓ Produto deletado em {delete_time*1000:.2f}ms")

        # Testar deleção em lote (primeiros 50)
        print("\n3. Testando deleção em lote (50 produtos)...")
        products_to_delete = SinglePiece.objects.filter(
            sku__startswith="PERF-"
        ).order_by("sku")[:50]

        start_time = time.time()
        count_before = SinglePiece.objects.count()

        for product in products_to_delete:
            self.client.post(reverse("product_delete", kwargs={"pk": product.pk}))

        batch_delete_time = time.time() - start_time
        count_after = SinglePiece.objects.count()

        print(f"   ✓ 50 produtos deletados em {batch_delete_time:.2f}s")
        print(f"   ✓ Taxa: {50/batch_delete_time:.1f} produtos/segundo")
        print(f"   ✓ Tempo médio: {batch_delete_time*1000/50:.2f}ms por produto")

        # Testar consulta após deleções
        print("\n4. Testando performance de consulta...")
        start_time = time.time()
        remaining = SinglePiece.objects.filter(sku__startswith="PERF-").count()
        query_time = time.time() - start_time

        print(f"   ✓ Produtos restantes: {remaining}")
        print(f"   ✓ Tempo de consulta: {query_time*1000:.2f}ms")

        # Limpar produtos de teste restantes
        print("\n5. Limpando produtos de teste...")
        start_time = time.time()
        deleted_count = SinglePiece.objects.filter(sku__startswith="PERF-").delete()[0]
        cleanup_time = time.time() - start_time

        print(f"   ✓ {deleted_count} produtos deletados em {cleanup_time:.2f}s")

        print("\n" + "=" * 60)
        print("RESUMO DO TESTE")
        print("=" * 60)
        print(f"Criação: {creation_time:.2f}s para 300 produtos")
        print(f"Deleção individual: {delete_time*1000:.2f}ms")
        print(f"Deleção em lote: {batch_delete_time:.2f}s para 50 produtos")
        print(f"Limpeza final: {cleanup_time:.2f}s para {deleted_count} produtos")
        print("=" * 60 + "\n")

    # =========================
    # Testes de Integridade
    # =========================

    def test_sku_unique_after_delete(self):
        """Após deletar, pode criar produto com mesmo SKU"""
        self.client.login(username="supervisor", password="test123")

        # Criar e deletar
        product1 = self.create_product("012", name="Produto Original")
        self.client.post(reverse("product_delete", kwargs={"pk": product1.pk}))

        # Criar novo com mesmo SKU
        product2 = self.create_product("012", name="Produto Novo")
        self.assertEqual(product2.sku, "012")
        self.assertEqual(product2.name, "Produto Novo")

    def test_category_remains_after_product_delete(self):
        """Categoria não é deletada quando produto é removido"""
        self.client.login(username="supervisor", password="test123")
        product = self.create_product("013")

        self.client.post(reverse("product_delete", kwargs={"pk": product.pk}))

        # Categoria ainda existe
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_delete_multiple_products_same_category(self):
        """Deletar múltiplos produtos da mesma categoria"""
        self.client.login(username="supervisor", password="test123")

        # Criar 5 produtos na mesma categoria
        for i in range(14, 19):
            self.create_product(f"0{i}")

        initial_count = SinglePiece.objects.count()

        # Deletar todos
        products = SinglePiece.objects.filter(sku__startswith="01")
        for product in products:
            self.client.post(reverse("product_delete", kwargs={"pk": product.pk}))

        final_count = SinglePiece.objects.count()
        self.assertLess(final_count, initial_count)


class ProductDeleteErrorHandlingTestCase(TestCase):
    """Testes de tratamento de erros na deleção"""

    def setUp(self):
        self.supervisor_group = Group.objects.create(name="Supervisor")
        self.supervisor = User.objects.create_user(
            username="supervisor", password="test123"
        )
        self.supervisor.groups.add(self.supervisor_group)
        self.client = Client()
        self.client.login(username="supervisor", password="test123")

        self.category = Category.objects.create(name="Test", is_active=True)

    def test_concurrent_delete_attempts(self):
        """Tentar deletar produto que já foi deletado"""
        product = SinglePiece.objects.create(
            sku="999",
            name="Test",
            category=self.category,
            thickness_mm=3,
            is_sellable=False,
        )

        # Primeira deleção
        response1 = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response1.status_code, 302)

        # Segunda tentativa (produto já não existe)
        response2 = self.client.post(
            reverse("product_delete", kwargs={"pk": product.pk})
        )
        self.assertEqual(response2.status_code, 404)

    def test_delete_with_invalid_pk(self):
        """Tentar deletar com PK inválido (não numérico não passa na URL)"""
        # A URL pattern só aceita [0-9]+, então PK inválido causa 404
        response = self.client.post(reverse("product_delete", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)
