from io import BytesIO
from datetime import datetime
import socket
import os
import qrcode
from reportlab.platypus import Image as RLImage

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import zoneinfo

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfgen import canvas as rl_canvas

from vendas.models import Order

# ── PALETA ───────────────────────────────────────────────────
C_PRIMARY    = colors.HexColor('#2C2C2C')
C_ACCENT     = colors.HexColor('#555555')
C_LIGHT_BG   = colors.HexColor('#F2F2F2')
C_BORDER     = colors.HexColor('#CBD5E1')
C_TEXT       = colors.HexColor('#1E293B')
C_TEXT_MUTED = colors.HexColor('#64748B')
C_WHITE      = colors.white
C_TOTAL_BG   = colors.HexColor('#E8E8E8')

# ── WATERMARK ────────────────────────────────────────────────
_WM_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'vendas', 'img', 'deco.png'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deco.png'),
    '/mnt/user-data/outputs/deco.png',
]

def _get_watermark_path():
    return next((p for p in _WM_PATHS if os.path.exists(p)), None)


# ── HELPERS ──────────────────────────────────────────────────
def _fmt_brl(value) -> str:
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _build_qr(url: str, size_mm: float) -> RLImage:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10, border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return RLImage(buf, width=size_mm * mm, height=size_mm * mm)


def _build_address(client) -> str:
    parts = []
    street = ''
    if getattr(client, 'street', None):
        street = client.street
        if getattr(client, 'number', None):     street += f', {client.number}'
        if getattr(client, 'complement', None): street += f' - {client.complement}'
    if street: parts.append(street)
    if getattr(client, 'neighborhood', None): parts.append(client.neighborhood)
    city = getattr(client, 'city', None) or ''
    if city:
        if getattr(client, 'state', None): city += f'/{client.state}'
        parts.append(city)
    if getattr(client, 'zip_code', None):
        cep = str(client.zip_code)
        if len(cep) == 8: cep = f'{cep[:5]}-{cep[5:]}'
        parts.append(f'CEP {cep}')
    return ' - '.join(parts) if parts else '—'


def _build_payments_text(order) -> str:
    from vendas.models.payment import Payment
    payments = order.payments.all()
    if not payments.exists():
        return '—'
    method_map = dict(Payment.Method.choices)
    lines = []
    for p in payments:
        line = f'{method_map.get(p.method, p.method)}   {_fmt_brl(p.amount)}'
        if p.transaction:
            line += f'   —  Nº Transação: {p.transaction}'
        lines.append(line)
    return '<br/>'.join(lines)


# ── ESTILOS ───────────────────────────────────────────────────
def _styles() -> dict:
    return {
        'company':     ParagraphStyle('company',     fontSize=18, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=22),
        'company_sub': ParagraphStyle('company_sub', fontSize=9,  textColor=C_TEXT_MUTED, fontName='Helvetica',      leading=13),
        'doc_number':  ParagraphStyle('doc_number',  fontSize=20, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=24, alignment=TA_RIGHT),
        'doc_label':   ParagraphStyle('doc_label',   fontSize=9,  textColor=C_TEXT_MUTED, fontName='Helvetica',      leading=13, alignment=TA_RIGHT),
        'section':     ParagraphStyle('section',     fontSize=8,  textColor=C_ACCENT,     fontName='Helvetica-Bold', spaceBefore=2, spaceAfter=4, leading=10),
        'label':       ParagraphStyle('label',       fontSize=8,  textColor=C_TEXT_MUTED, fontName='Helvetica',      leading=11),
        'value':       ParagraphStyle('value',       fontSize=9,  textColor=C_TEXT,       fontName='Helvetica-Bold', leading=13),
        'th':          ParagraphStyle('th',          fontSize=8,  textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=11),
        'td':          ParagraphStyle('td',          fontSize=8.5,textColor=C_TEXT,       fontName='Helvetica',      leading=12),
        'td_bold':     ParagraphStyle('td_bold',     fontSize=8.5,textColor=C_TEXT,       fontName='Helvetica-Bold', leading=12),
        'total_label': ParagraphStyle('total_label', fontSize=9,  textColor=C_TEXT_MUTED, fontName='Helvetica',      leading=13, alignment=TA_RIGHT),
        'total_value': ParagraphStyle('total_value', fontSize=9,  textColor=C_TEXT,       fontName='Helvetica-Bold', leading=13, alignment=TA_LEFT),
        'grand_label': ParagraphStyle('grand_label', fontSize=11, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=15, alignment=TA_RIGHT),
        'grand_value': ParagraphStyle('grand_value', fontSize=11, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=15, alignment=TA_LEFT),
        'obs':         ParagraphStyle('obs',         fontSize=8.5,textColor=C_TEXT,       fontName='Helvetica',      leading=13),
        'footer':      ParagraphStyle('footer',      fontSize=7.5,textColor=C_TEXT_MUTED, fontName='Helvetica',      leading=10),
    }


def _section_title(text: str, s: dict) -> Paragraph:
    return Paragraph(text.upper(), s['section'])


def _info_grid(rows: list, col_widths: list, s: dict) -> Table:
    """Grade de label/valor com fundo alternado."""
    table_rows = []
    for row_pair in rows:
        cells = []
        for label, value in row_pair:
            cells.append(Paragraph(label, s['label']))
            if isinstance(value, list):
                cells.append(Paragraph(' - '.join(v for v in value if v) or '—', s['value']))
            else:
                cells.append(Paragraph(str(value) if value else '—', s['value']))
        table_rows.append(cells)

    t = Table(table_rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        *[('BACKGROUND', (0, i), (-1, i), C_LIGHT_BG) for i in range(0, len(table_rows), 2)],
    ]))
    return t


def _full_width_row(label: str, value: str, col_lbl: float, content_w: float, s: dict, bg=None) -> Table:
    """Linha simples label + valor ocupando largura total."""
    t = Table(
        [[Paragraph(label, s['label']), Paragraph(value, s['value'])]],
        colWidths=[col_lbl, content_w - col_lbl],
    )
    style = [
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]
    if bg:
        style.append(('BACKGROUND', (0, 0), (-1, -1), bg))
    t.setStyle(TableStyle(style))
    return t


# ── VIEW PRINCIPAL ────────────────────────────────────────────
def order_pdf(request, pk):
    order      = get_object_or_404(Order.objects.select_related('client', 'created_by'), pk=pk)
    client_obj = order.client
    wm_path    = _get_watermark_path()
    s          = _styles()
    now_str    = datetime.now(tz=zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    now_header = datetime.now(tz=zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime('%d/%m/%Y  %H:%M')

    buffer    = BytesIO()
    PAGE_W, PAGE_H = A4
    MARGIN    = 10 * mm
    CONTENT_W = PAGE_W - 2 * MARGIN
    HEADER_H  = 35 * mm

    col_lbl = 26 * mm
    col_val = CONTENT_W / 2 - col_lbl
    cw      = [col_lbl, col_val, col_lbl, col_val]

    # ── Canvas com marca d'água ───────────────────────────────
    class WatermarkCanvas(rl_canvas.Canvas):
        def showPage(self):
            if wm_path:
                self.saveState()
                from PIL import Image as PILImage
                with PILImage.open(wm_path) as _im:
                    orig_w, orig_h = _im.size
                scale  = HEADER_H / orig_h
                draw_w = orig_w * scale
                draw_x = MARGIN + (CONTENT_W - draw_w) / 2
                self.drawImage(
                    wm_path, draw_x, PAGE_H - MARGIN - HEADER_H,
                    width=draw_w, height=HEADER_H,
                    mask='auto', preserveAspectRatio=False,
                )
                self.restoreState()
            super().showPage()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title=f"Pedido #{order.number}", author='Decorcril',
    )

    elements = []

    # ── CABEÇALHO ─────────────────────────────────────────────
    left_col = [
        Paragraph("DECORCRIL", s['company']),
        Spacer(1, 2 * mm),
        Paragraph("Decorcril Acrílicos e Artesanatos Ltda.", s['company_sub']),
        Paragraph("Rua Prudente de Moraes, 1327 - Suzano/SP", s['company_sub']),
        Paragraph("CNPJ: 45.401.044/0001-61", s['company_sub']),
        Paragraph('WhatsApp: (11)97899-9091', s['company_sub']),
    ]
    right_col = [
        Paragraph("PEDIDO DE VENDA", s['doc_label']),
        Paragraph(f"Nº {order.number}", s['doc_number']),
        Spacer(1, 2 * mm),
        Paragraph(f"Emissão: {now_header}", s['doc_label']),
    ]
    header_table = Table(
        [[left_col, right_col]],
        colWidths=[CONTENT_W * 0.55, CONTENT_W * 0.45],
        rowHeights=[HEADER_H],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4 * mm),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4 * mm),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceBefore=3*mm, spaceAfter=4*mm))

    # ── DADOS DO CLIENTE ──────────────────────────────────────
    elements.append(_section_title('Dados do Cliente', s))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_info_grid([
        [('Cliente',    client_obj.name),
         ('Pedido Nº',  order.number)],
        [('CNPJ / CPF', getattr(client_obj, 'document', None)),
         ('Data',       order.created_at.strftime('%d/%m/%Y'))],
        [('Telefone',   getattr(client_obj, 'phone', None)),
         ('Situação',   order.get_status_display())],
        [('E-mail',     getattr(client_obj, 'email', None)),
         ('Contato',    getattr(client_obj, 'contact_person', None))],
    ], cw, s))
    elements.append(_full_width_row('Endereço', _build_address(client_obj), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    elements.append(Spacer(1, 4 * mm))

    # ── DADOS COMERCIAIS ──────────────────────────────────────
    elements.append(_section_title('Dados Comerciais', s))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_info_grid([
        [('Vendedor', str(order.created_by.get_full_name())),
         ('Tipo de Venda',  order.get_sale_type_display() if order.sale_type else None)],
        [('Transportadora', getattr(order, 'carrier', None)),
         ('Pagamento', getattr(order, 'payment_terms', None))],
    ], cw, s))
    if order.payments.exists():
        elements.append(_full_width_row('Pagamentos', _build_payments_text(order), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    elements.append(Spacer(1, 4 * mm))

    # ── ITENS DO PEDIDO ───────────────────────────────────────
    elements.append(_section_title('Itens do Pedido', s))
    elements.append(Spacer(1, 2 * mm))
    elements += _build_items_table(order, CONTENT_W, s)
    elements.append(Spacer(1, 4 * mm))

    # ── OBSERVAÇÕES ───────────────────────────────────────────
    if order.notes:
        elements.append(_section_title('Observações', s))
        elements.append(Spacer(1, 2 * mm))
        obs_table = Table([[Paragraph(order.notes, s['obs'])]], colWidths=[CONTENT_W])
        obs_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), C_LIGHT_BG),
            ('BOX',           (0, 0), (-1, -1), 0.5, C_BORDER),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5 * mm),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 5 * mm),
            ('TOPPADDING',    (0, 0), (-1, -1), 4 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4 * mm),
        ]))
        elements.append(obs_table)
        elements.append(Spacer(1, 4 * mm))

    # ── RESUMO FINANCEIRO ─────────────────────────────────────
    elements.append(_section_title('Resumo Financeiro', s))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_build_totals_table(order, CONTENT_W, s))
    elements.append(Spacer(1, 8 * mm))

    # ── RODAPÉ ────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceAfter=3 * mm))
    elements.append(_build_footer(request, order, CONTENT_W, now_str, s))

    doc.build(elements, canvasmaker=WatermarkCanvas)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="pedido_{order.number}.pdf"'
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response


# ── SEÇÕES EXTRAÍDAS ──────────────────────────────────────────
def _build_items_table(order, content_w: float, s: dict):
    items_qs     = order.items.select_related('product__category').all()
    has_discount = any(item.discount > 0 for item in items_qs)

    def _th(text):     return Paragraph(text, s['th'])
    def _th_c(text):   return Paragraph(text, ParagraphStyle('thC', parent=s['th'], alignment=TA_CENTER))
    def _td(text):     return Paragraph(str(text), s['td'])
    def _td_c(text):   return Paragraph(str(text), ParagraphStyle('tdC', parent=s['td'], alignment=TA_CENTER))
    def _td_r(text, bold=False):
        return Paragraph(str(text), ParagraphStyle('tdR', parent=s['td_bold'] if bold else s['td'], alignment=TA_RIGHT))

    def _desc(p) -> str:
        parts = [f'<b>{p.name}</b>']
        attrs = []
        if getattr(p, 'acrylic_color', None):    attrs.append(p.get_acrylic_color_display())
        if getattr(p, 'color_observation', None): attrs.append(p.color_observation)
        if getattr(p, 'has_led', False) and getattr(p, 'led_type', None):
            attrs.append(f'LED {p.get_led_type_display()}')
        if getattr(p, 'voltage', None):           attrs.append(p.get_voltage_display())
        if attrs:
            parts.append(f'<font color="#666666" size="7.5">{" · ".join(attrs)}</font>')
        return '<br/>'.join(parts)

    def _measures(p) -> str:
        cm_vals = [f'{v:g}'.replace('.', ',') for v in [
            getattr(p, 'width_cm',     None), getattr(p, 'height_cm',    None),
            getattr(p, 'length_cm',    None), getattr(p, 'diameter_cm',  None),
            getattr(p, 'depth_cm',     None), getattr(p, 'curvature_cm', None),
        ] if v]
        parts = []
        if cm_vals: parts.append(' × '.join(cm_vals) + ' cm')
        if getattr(p, 'thickness_mm', None): parts.append(f'{p.thickness_mm} mm')
        return ' / '.join(parts) if parts else '—'

    COL_ITEM  = 6  * mm
    COL_QTD   = 9  * mm
    COL_SKU   = 15 * mm
    COL_MEAS  = 48 * mm
    COL_PRICE = 18 * mm
    COL_DISC  = 20 * mm if has_discount else 0
    COL_TOTAL = 22 * mm
    COL_DESC  = content_w - COL_ITEM - COL_QTD - COL_SKU - COL_MEAS - COL_PRICE - COL_DISC - COL_TOTAL

    header_row = [_th('#'), _th_c('Qtd'), _th('Cod'), _th('Descrição'), _th('Medidas'), _th_c('Vlr. Unit.')]
    col_widths  = [COL_ITEM, COL_QTD, COL_SKU, COL_DESC, COL_MEAS, COL_PRICE]
    if has_discount:
        header_row.append(_th_c('Desconto'))
        col_widths.append(COL_DISC)
    header_row.append(_th_c('Total'))
    col_widths.append(COL_TOTAL)

    meas_style = ParagraphStyle('meas', parent=s['td'], fontSize=7.5, leading=11)
    rows = [header_row]
    for i, item in enumerate(items_qs, 1):
        p = item.product
        row = [
            _td(i), _td_c(item.quantity), _td(p.sku),
            Paragraph(_desc(p), s['td']),
            Paragraph(_measures(p), meas_style),
            _td_r(_fmt_brl(item.unit_price)),
        ]
        if has_discount:
            row.append(_td_r(_fmt_brl(item.discount) if item.discount > 0 else '—'))
        row.append(_td_r(_fmt_brl(item.subtotal), bold=True))
        rows.append(row)

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0),  (-1, 0),  C_LIGHT_BG),
        ('TOPPADDING',     (0, 0),  (-1, 0),  5),
        ('BOTTOMPADDING',  (0, 0),  (-1, 0),  5),
        ('ROWBACKGROUNDS', (0, 1),  (-1, -1), [C_WHITE, C_LIGHT_BG]),
        ('GRID',           (0, 0),  (-1, -1), 0.4, C_BORDER),
        ('VALIGN',         (0, 0),  (-1, -1), 'TOP'),
        ('ALIGN',          (1, 1),  (1, -1),  'CENTER'),
        ('ALIGN',          (5, 1),  (-1, -1), 'RIGHT'),
        ('LEFTPADDING',    (0, 0),  (-1, -1), 4),
        ('RIGHTPADDING',   (0, 0),  (-1, -1), 4),
        ('TOPPADDING',     (0, 1),  (-1, -1), 5),
        ('BOTTOMPADDING',  (0, 1),  (-1, -1), 5),
        ('TEXTCOLOR',      (4, 1),  (4, -1),  C_TEXT_MUTED),
    ]))
    return [t]


def _build_totals_table(order, content_w: float, s: dict) -> Table:
    """
    total_products = soma bruta (unit_price × qty), sem desconto
    total_discount = soma dos descontos
    total_amount   = total_products - total_discount + freight
    """
    COL_SPACER = content_w * 0.45
    COL_LBL    = content_w * 0.30
    COL_VAL    = content_w * 0.25

    rows = []
    # Só exibe bruto/desconto se houver desconto
    if order.total_discount > 0:
        rows.append(('Total Bruto:',   _fmt_brl(order.total_products), False))
        rows.append(('(-) Descontos:', _fmt_brl(order.total_discount), False))

    rows += [
        ('Total Produtos:', _fmt_brl(order.total_products - order.total_discount), False),
        ('(+) Frete:',      _fmt_brl(order.freight),                               False),
        ('Total Geral:',    _fmt_brl(order.total_amount),                          True),
        ('Total Pago:',     _fmt_brl(order.total_paid),                            False),
        ('Saldo a Pagar:',  _fmt_brl(order.remaining),                             False),
    ]
    grand_idx = next(i for i, r in enumerate(rows) if r[2])

    data = [
        [Paragraph('', s['total_label']),
         Paragraph(label, s['grand_label'] if grand else s['total_label']),
         Paragraph(value, s['grand_value'] if grand else s['total_value'])]
        for label, value, grand in rows
    ]

    t = Table(data, colWidths=[COL_SPACER, COL_LBL, COL_VAL])
    t.setStyle(TableStyle([
        ('VALIGN',        (0, 0),  (-1, -1),  'MIDDLE'),
        ('TOPPADDING',    (0, 0),  (-1, -1),  3),
        ('BOTTOMPADDING', (0, 0),  (-1, -1),  3),
        ('RIGHTPADDING',  (1, 0),  (1, -1),   4),
        ('LEFTPADDING',   (2, 0),  (2, -1),   6),
        ('BACKGROUND',    (1, grand_idx), (2, grand_idx), C_TOTAL_BG),
        ('LINEABOVE',     (1, grand_idx), (2, grand_idx), 0.7, C_ACCENT),
        ('LINEBELOW',     (1, grand_idx), (2, grand_idx), 0.7, C_ACCENT),
        ('TOPPADDING',    (0, grand_idx), (-1, grand_idx), 5),
        ('BOTTOMPADDING', (0, grand_idx), (-1, grand_idx), 5),
        ('LINEABOVE',     (1, len(rows)-1), (2, len(rows)-1), 0.4, C_BORDER),
    ]))
    return t


def _build_footer(request, order, content_w: float, now_str: str, s: dict) -> Table:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
    except Exception:
        local_ip = request.get_host()

    order_url = f'http://{local_ip}:{request.get_port()}/vendas/pedidos/{order.pk}/'
    qr_img    = _build_qr(order_url, size_mm=22)

    footer_text = [
        Paragraph(f'Documento gerado eletronicamente em {now_str} — Decorcril System', s['footer']),
        Spacer(1, 2 * mm),
        Paragraph(f'Pedido Nº {order.number}  •  Página 1 de 1', s['footer']),
        Spacer(1, 2 * mm),
        Paragraph('<font color="#555555">Aponte a câmera para visualizar este pedido</font>',
                  ParagraphStyle('qr_hint', parent=s['footer'], fontSize=7)),
    ]
    t = Table([[footer_text, qr_img]], colWidths=[content_w - 26 * mm, 26 * mm])
    t.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (1, 0), (1, 0),   'RIGHT'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (0, 0),   4),
        ('RIGHTPADDING',  (1, 0), (1, 0),   0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t