from django.apps import AppConfig

class VendasConfig(AppConfig):
    name = "vendas"

    def ready(self):
        pass  # não precisa mais importar signals