from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors

from vendas.models import Order


def order_pdf(request, pk):

    order = get_object_or_404(Order.objects.select_related("client", "created_by"), pk=pk)

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    bold = styles["Heading4"]

    elements = []

    # =========================
    # CABEÇALHO
    # =========================

    header_data = [
        ["DECORCRIL ACRÍLICOS E ARTESANATOS LTDA"],
        ["Rua Prudente de Moraes, 1327 - Suzano/SP"],
        ["CNPJ: 45.401.044/0001-61"],
    ]

    header = Table(header_data)
    header.setStyle(TableStyle([
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("FONTSIZE",(0,0),(-1,-1),10)
    ]))

    elements.append(header)
    elements.append(Spacer(1,10))

    # =========================
    # TITULO
    # =========================

    title = Table([["PEDIDO DE VENDA"]])
    title.setStyle(TableStyle([
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("FONTSIZE",(0,0),(-1,-1),14),
        ("BOX",(0,0),(-1,-1),1,colors.black)
    ]))

    elements.append(title)
    elements.append(Spacer(1,10))

    # =========================
    # RESUMO PEDIDO
    # =========================

    resumo_data = [[
        "Cliente", order.client.name,
        "Pedido", order.number,
        "Data", order.created_at.strftime("%d/%m/%Y"),
        "Situação", order.get_status_display(),
    ]]

    resumo = Table(resumo_data, colWidths=[60,120,50,80,40,80,50,80])
    resumo.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("FONTSIZE",(0,0),(-1,-1),9)
    ]))

    elements.append(resumo)
    elements.append(Spacer(1,10))

    # =========================
    # DADOS CLIENTE
    # =========================

    client = order.client

    client_data = [
        ["Nome", client.name, "Documento", getattr(client,"document","")],
        ["Telefone", getattr(client,"phone",""), "Email", getattr(client,"email","")],
    ]

    client_table = Table(client_data, colWidths=[80,200,80,200])
    client_table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("FONTSIZE",(0,0),(-1,-1),9)
    ]))

    elements.append(client_table)
    elements.append(Spacer(1,10))

    # =========================
    # DADOS COMERCIAIS
    # =========================

    comercial_data = [
        ["Representante", str(order.created_by)],
        ["Tipo venda", order.get_sale_type_display()],
        ["Condição pagamento", order.payment_terms],
        ["Transportadora", order.carrier],
    ]

    comercial_table = Table(comercial_data, colWidths=[150,350])
    comercial_table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("FONTSIZE",(0,0),(-1,-1),9)
    ]))

    elements.append(comercial_table)
    elements.append(Spacer(1,10))

    # =========================
    # ITENS
    # =========================

    items_data = [
        ["Qtd", "Un", "Descrição", "Valor Unit", "Valor Total"]
    ]

    for item in order.items.all():

        descricao = item.product.name

        if hasattr(item.product, "thickness_mm") and item.product.thickness_mm:
            descricao += f" - {item.product.thickness_mm}mm"

        if hasattr(item.product, "acrylic_color") and item.product.acrylic_color:
            descricao += f" - {item.product.acrylic_color}"

        items_data.append([
            item.quantity,
            "CJ",
            descricao,
            f"{item.unit_price}",
            f"{item.subtotal}"
        ])

    items_table = Table(items_data, colWidths=[40,40,250,100,100])

    items_table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
        ("ALIGN",(0,1),(1,-1),"CENTER"),
        ("ALIGN",(3,1),(4,-1),"RIGHT"),
        ("FONTSIZE",(0,0),(-1,-1),9)
    ]))

    elements.append(items_table)
    elements.append(Spacer(1,10))

    # =========================
    # OBSERVAÇÃO
    # =========================

    obs = Paragraph(f"<b>Observação:</b> {order.notes or ''}", normal)

    elements.append(obs)
    elements.append(Spacer(1,10))

    # =========================
    # TOTAIS
    # =========================

    totals_data = [
        ["Total Produtos", order.total_products],
        ["Frete", order.freight],
        ["Total Geral", order.total_amount],
        ["Total Pago", order.total_paid],
        ["Saldo", order.remaining],
    ]

    totals = Table(totals_data, colWidths=[200,150])
    totals.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("ALIGN",(1,0),(1,-1),"RIGHT"),
        ("FONTSIZE",(0,0),(-1,-1),10)
    ]))

    elements.append(totals)

    # =========================
    # BUILD PDF
    # =========================

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pedido_{order.number}.pdf"'
    response.write(pdf)

    return response