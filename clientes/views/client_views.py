from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.contrib import messages
from catalogo.decorators import group_required

from ..models.client import Client
from ..forms.client_form import (
    ClientForm,
    ClientFormSupervisor,
    ClientFormVendedor
)


# =====================================================
# LISTAGEM + CREATE
# =====================================================
@group_required("Supervisor", "Vendedor")
def clients_list_view(request):

    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente criado com sucesso.")
            return redirect("clientes:clients_list")
        else:
            messages.error(request, "Erro ao criar cliente. Verifique os campos.")
    else:
        form = ClientForm()

    query = request.GET.get("q", "").strip()

    clients = Client.objects.only(
        "id", "code", "name", "document",
        "email", "phone", "city", "state", "created_at"
    )

    if query:
        clients = clients.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(document__icontains=query)
        )

    clients = clients.order_by("name")

    is_supervisor = request.user.groups.filter(name="Supervisor").exists()
    is_vendedor   = request.user.groups.filter(name="Vendedor").exists()

    context = {
        "clients": clients,
        "form": form,
        "query": query,
        "page_title": "Clientes",
        "is_supervisor": is_supervisor,
        "is_vendedor": is_vendedor,
    }

    return render(request, "clientes/clients/list.html", context)


# =====================================================
# UPDATE (MODAL AJAX)
# =====================================================
@group_required("Supervisor", "Vendedor")
def client_update_view(request, pk):
    client = get_object_or_404(Client, pk=pk)

    is_supervisor = request.user.groups.filter(name="Supervisor").exists()
    is_vendedor   = request.user.groups.filter(name="Vendedor").exists()
    FormClass     = ClientFormSupervisor if is_supervisor else ClientFormVendedor

    if request.method == "POST":
        form = FormClass(request.POST, instance=client)

        if form.is_valid():
            client = form.save()

            ctx = {
                "client": client,
                "is_supervisor": is_supervisor,
                "is_vendedor": is_vendedor,
            }

            row_html = render(request, "clientes/clients/_row.html", ctx).content.decode("utf-8")

            # HTML dos dois modais juntos — substitui o #client-modals-{pk} no DOM
            view_modal_html = render(request, "clientes/clients/_view_modal.html", ctx).content.decode("utf-8")
            edit_modal_html = render(request, "clientes/clients/_edit_modal.html", ctx).content.decode("utf-8")
            modals_html = view_modal_html + edit_modal_html

            return JsonResponse({
                "success": True,
                "client_id": client.pk,
                "row_html": row_html,
                "modals_html": modals_html,
            })

        html = render(
            request,
            "clientes/clients/_edit_modal.html",
            {"form": form, "client": client, "is_supervisor": is_supervisor}
        ).content.decode("utf-8")

        return JsonResponse({"success": False, "html": html})

    # GET — retorna modal de edição para o AJAX carregar
    form = FormClass(instance=client)

    return render(
        request,
        "clientes/clients/_edit_modal.html",
        {"form": form, "client": client, "is_supervisor": is_supervisor}
    )


# =====================================================
# CHECK DOCUMENT (AJAX)
# =====================================================
@group_required("Supervisor", "Vendedor")
def check_document_view(request):
    document = request.GET.get("document", "").strip()
    digits   = "".join(filter(str.isdigit, document))

    if not digits:
        return JsonResponse({"exists": False})

    client = Client.objects.filter(
        Q(document=document) | Q(document=digits)
    ).first()

    if client:
        return JsonResponse({"exists": True, "name": client.name})

    return JsonResponse({"exists": False})