from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from vendas.models import Order

# View COM login (para uso interno)
class OrderQRDetailView(LoginRequiredMixin, View):
    login_url = 'login'
    
    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related('client', 'created_by')
                        .prefetch_related('items__product', 'payments'), 
            pk=pk
        )
        
        return render(request, 'vendas/orders/qr_detail.html', {'order': order})

# View SEM login (pública para QR code)
class OrderQRPublicView(View):
    """
    View pública para QR code - NÃO exige autenticação
    """
    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related('client', 'created_by')
                        .prefetch_related('items__product', 'payments'), 
            pk=pk
        )
        
        return render(request, 'vendas/orders/qr_detail.html', {'order': order})