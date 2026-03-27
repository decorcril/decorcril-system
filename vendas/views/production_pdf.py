"""
production_pdf.py
Ordem de Produção — documento interno simples.
Sem informações de valores (preços, descontos, totais financeiros) e sem QR code.
"""
from io import BytesIO
from datetime import datetime
import os
import zoneinfo

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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

# ── WATERMARK ────────────────────────────────────────────────
_WM_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'vendas', 'img', 'deco.png'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deco.png'),
]

def _get_watermark_path():
    return next((p for p in _WM_PATHS if os.path.exists(p)), None)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _build_address(client) -> str:
    parts, street = [], ''
    if getattr(client, 'street', None):
        street = client.street
        if getattr(client, 'number', None): street += f', {client.number}'
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


def _product_details(p) -> str:
    """Linha de detalhes discreta abaixo do nome: medidas · cor · elétrica."""

    def _fmt_v(v):
        try:
            return f'{float(v):g}'
        except (TypeError, ValueError):
            return ''

    def _piece_details(piece) -> str:
        parts = []
        if getattr(piece, 'thickness_mm', None):
            parts.append(f'{piece.thickness_mm} mm')
        cm_fields = ['length_cm', 'width_cm', 'diameter_cm',
                     'depth_cm', 'curvature_cm', 'height_cm']
        cm_vals = [_fmt_v(getattr(piece, f, None))
                   for f in cm_fields if getattr(piece, f, None)]
        if cm_vals:
            parts.append(' × '.join(cm_vals) + ' cm')
        if getattr(piece, 'acrylic_color', None):
            color_map = dict(piece.ACRYLIC_COLOR_CHOICES)
            parts.append(color_map.get(piece.acrylic_color, piece.acrylic_color))
        if getattr(piece, 'color_observation', None):
            parts.append(piece.color_observation)
        if getattr(piece, 'has_led', False) and getattr(piece, 'led_type', None):
            led_map = dict(piece.LED_TYPE_CHOICES)
            parts.append(f'LED {led_map.get(piece.led_type, piece.led_type)}')
        if getattr(piece, 'voltage', None):
            voltage_map = {k: v for k, v in piece.VOLTAGE_CHOICES if k}
            parts.append(voltage_map.get(piece.voltage, piece.voltage))
        return ' · '.join(parts)

    # Produto composto — usa list() para aproveitar cache do prefetch_related
    components = list(p.components.all())
    if not p.is_kit and components:
        lines = []
        for c in components:
            det = _piece_details(c.component)
            qty = f'{c.quantity}x ' if c.quantity > 1 else ''
            lines.append(
                f'<b>{qty}{c.component.name}:</b> {det}' if det
                else f'<b>{qty}{c.component.name}</b>'
            )
        return '<br/>'.join(lines) if lines else ''

    return _piece_details(p)


# ══════════════════════════════════════════════════════════════
# ESTILOS
# ══════════════════════════════════════════════════════════════

def _styles() -> dict:
    return {
        'company':     ParagraphStyle('company',     fontSize=18, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=22),
        'company_sub': ParagraphStyle('company_sub', fontSize=9,  textColor=C_PRIMARY,    fontName='Helvetica',      leading=13),
        'doc_number':  ParagraphStyle('doc_number',  fontSize=20, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=24, alignment=TA_RIGHT),
        'doc_label':   ParagraphStyle('doc_label',   fontSize=9,  textColor=C_PRIMARY,    fontName='Helvetica',      leading=13, alignment=TA_RIGHT),
        'section':     ParagraphStyle('section',     fontSize=10, textColor=C_PRIMARY,    fontName='Helvetica-Bold', spaceBefore=2, spaceAfter=4, leading=12),
        'label':       ParagraphStyle('label',       fontSize=10, textColor=colors.black, fontName='Helvetica-Bold', leading=11),
        'value':       ParagraphStyle('value',       fontSize=10, textColor=colors.black, fontName='Helvetica',      leading=13),
        'th':          ParagraphStyle('th',          fontSize=8,  textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=11),
        'td':          ParagraphStyle('td',          fontSize=8.5,textColor=colors.black, fontName='Helvetica-Bold', leading=12),
        'td_bold':     ParagraphStyle('td_bold',     fontSize=8.5,textColor=colors.black, fontName='Helvetica-Bold', leading=12),
        'td_sub':      ParagraphStyle('td_sub',      fontSize=8,  textColor=colors.black, fontName='Helvetica',      leading=11),
        'obs':         ParagraphStyle('obs',         fontSize=8.5,textColor=colors.black, fontName='Helvetica',      leading=13),
    }

def _section_title(text: str, s: dict) -> Paragraph:
    return Paragraph(text.upper(), s['section'])


def _info_grid(rows: list, col_widths: list, s: dict) -> Table:
    table_rows = []
    for row_pair in rows:
        cells = []
        for label, value in row_pair:
            cells.append(Paragraph(label, s['label']))
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


# ══════════════════════════════════════════════════════════════
# TABELA DE ITENS
# ══════════════════════════════════════════════════════════════

def _build_items_table(order, content_w: float, s: dict) -> list:
    items_qs = (
        order.items
        .select_related('product__category')
        .prefetch_related('product__components__component')
        .all()
    )

    def _th(text):
        return Paragraph(text, s['th'])

    def _th_c(text):
        return Paragraph(text, ParagraphStyle('thC', parent=s['th'], alignment=TA_CENTER))

    def _td_c(text):
        return Paragraph(str(text), ParagraphStyle('tdC', parent=s['td'], alignment=TA_CENTER))

    def _td_desc(name: str, details: str):
        name_p = Paragraph(name, s['td_bold'])
        if details:
            detail_p = Paragraph(details, s['td_sub'])
            inner = Table([[name_p], [detail_p]], colWidths=None)
            inner.setStyle(TableStyle([
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            return inner
        return name_p

    COL_QTD  = 12 * mm
    COL_SKU  = 25 * mm
    COL_DESC = content_w - COL_QTD - COL_SKU
    col_widths = [COL_QTD, COL_SKU, COL_DESC]

    rows = [[_th_c('Qtd'), _th('Código'), _th('Descrição do Produto')]]
    style_cmds = [
        ('BACKGROUND',    (0, 0),  (-1, 0),  C_LIGHT_BG),
        ('TOPPADDING',    (0, 0),  (-1, 0),  5),
        ('BOTTOMPADDING', (0, 0),  (-1, 0),  5),
        ('GRID',          (0, 0),  (-1, -1), 0.4, C_BORDER),
        ('VALIGN',        (0, 0),  (-1, -1), 'TOP'),
        ('ALIGN',         (0, 1),  (0, -1),  'CENTER'),
        ('LEFTPADDING',   (0, 0),  (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0),  (-1, -1), 4),
        ('TOPPADDING',    (0, 1),  (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1),  (-1, -1), 5),
    ]

    for i, item in enumerate(items_qs, 1):
        p       = item.product
        details = _product_details(p)
        rows.append([
            _td_c(item.quantity),
            Paragraph(p.sku or '—', s['td']),
            _td_desc(p.name, details),
        ])
        bg = C_WHITE if i % 2 == 1 else C_LIGHT_BG
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return [t]


# ══════════════════════════════════════════════════════════════
# CANVAS COM MARCA D'ÁGUA E NUMERAÇÃO
# ══════════════════════════════════════════════════════════════

def _make_canvas_class(wm_path, page_w, page_h, margin, content_w, header_h):
    class WatermarkCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for page_num, state in enumerate(self._pages, 1):
                self.__dict__.update(state)

                if page_num == 1:
                    if wm_path:
                        self.saveState()
                        from PIL import Image as PILImage
                        with PILImage.open(wm_path) as im:
                            orig_w, orig_h = im.size
                        scale  = header_h / orig_h
                        draw_w = orig_w * scale
                        draw_x = margin + (content_w - draw_w) / 2
                        self.drawImage(
                            wm_path, draw_x, page_h - margin - header_h,
                            width=draw_w, height=header_h,
                            mask='auto', preserveAspectRatio=False,
                        )
                        self.restoreState()
                else:
                    self.saveState()
                    self.setFont('Helvetica-Bold', 9)
                    self.setFillColor(C_PRIMARY)
                    self.drawString(margin, page_h - margin + 1 * mm, "DECORCRIL — Ordem de Produção")
                    self.setLineWidth(0.4)
                    self.setStrokeColor(C_BORDER)
                    self.line(margin, page_h - margin - 1 * mm, page_w - margin, page_h - margin - 1 * mm)
                    self.restoreState()

                self.saveState()
                self.setFont('Helvetica', 7.5)
                self.setFillColor(colors.HexColor('#64748B'))
                self.drawRightString(
                    page_w - margin, page_h - margin + 2 * mm,
                    f'Página {page_num} de {total}',
                )
                self.restoreState()
                super().showPage()
            super().save()

    return WatermarkCanvas

# ══════════════════════════════════════════════════════════════
# VIEW PRINCIPAL
# ══════════════════════════════════════════════════════════════

def production_pdf_view(request, pk):
    order      = get_object_or_404(Order.objects.select_related('client', 'created_by'), pk=pk)
    client_obj = order.client
    s          = _styles()
    now_header = datetime.now(tz=zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime('%d/%m/%Y  %H:%M')

    PAGE_W, PAGE_H = A4
    MARGIN    = 6 * mm
    CONTENT_W = PAGE_W - 2 * MARGIN
    HEADER_H  = 35 * mm
    col_lbl   =30 * mm
    col_val   = CONTENT_W / 2 - col_lbl
    cw        = [col_lbl, col_val, col_lbl, col_val]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=f"Ordem de Produção #{order.number}", author='Decorcril',
    )

    el = []

    # ── Cabeçalho ─────────────────────────────────────────────
    left_col = [
        Paragraph("DECORCRIL", s['company']),
        Spacer(1, 2 * mm),
        Paragraph("Decorcril Acrílicos e Artesanatos Ltda.", s['company_sub']),
        Paragraph("Rua Prudente de Moraes, 1327 — Suzano/SP", s['company_sub']),
        Paragraph("CNPJ: 45.401.044/0001-61",                 s['company_sub']),
        Paragraph("WhatsApp: (11)97899-9091",                 s['company_sub']),
    ]
    right_col = [
        Paragraph("ORDEM DE PRODUÇÃO",   s['doc_label']),
        Paragraph(f"Nº {order.number}",  s['doc_number']),
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
    el.append(header_table)
    el.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceBefore=3*mm, spaceAfter=4*mm))

    # ── Dados do Cliente ──────────────────────────────────────
    el.append(_section_title('Dados do Cliente', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_info_grid([
        [('Cliente',    client_obj.name),                    ('Pedido Nº', order.number)],
        [('CNPJ / CPF', client_obj.document_display or '—'), ('Data',      order.created_at.strftime('%d/%m/%Y'))],
        [('Telefone',   client_obj.phone_display or '—'),    ('Situação',  order.get_status_display())],
    ], cw, s))
    el.append(_full_width_row('Endereço', _build_address(client_obj), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    el.append(Spacer(1, 4 * mm))

    # ── Dados Comerciais ──────────────────────────────────────
    el.append(_section_title('Informações do Pedido', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_info_grid([
        [('Vendedor',       order.created_by.get_full_name() or order.created_by.username),
         ('Tipo de Venda',  order.get_sale_type_display() if order.sale_type else '—')],
        [('Transportadora', order.carrier or '—'),
         ('Pagamento',      order.payment_terms or '—')],
    ], cw, s))
    el.append(Spacer(1, 4 * mm))

    # ── Itens do Pedido ───────────────────────────────────────
    el.append(_section_title('Itens do Pedido', s))
    el.append(Spacer(1, 2 * mm))
    el += _build_items_table(order, CONTENT_W, s)
    el.append(Spacer(1, 4 * mm))

    # ── Observações ──────────────────────────────────────────
    if order.notes or order.internal_notes:
        el.append(_section_title('Observações', s))
        el.append(Spacer(1, 2 * mm))
        if order.notes:
            obs_table = Table([[Paragraph(order.notes, s['obs'])]], colWidths=[CONTENT_W])
            obs_table.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), C_LIGHT_BG),
                ('BOX',           (0, 0), (-1, -1), 0.5, C_BORDER),
                ('LEFTPADDING',   (0, 0), (-1, -1), 5 * mm),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 5 * mm),
                ('TOPPADDING',    (0, 0), (-1, -1), 4 * mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4 * mm),
            ]))
            el.append(obs_table)
            el.append(Spacer(1, 2 * mm))
        if order.internal_notes:
            internal_style = ParagraphStyle('obs_internal', parent=s['obs'], textColor=colors.HexColor('#92400E'))
            internal_table = Table([[Paragraph(order.internal_notes, internal_style)]], colWidths=[CONTENT_W])
            internal_table.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#FFFBEB')),
                ('BOX',           (0, 0), (-1, -1), 0.5, colors.HexColor('#FBBF24')),
                ('LEFTPADDING',   (0, 0), (-1, -1), 5 * mm),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 5 * mm),
                ('TOPPADDING',    (0, 0), (-1, -1), 4 * mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4 * mm),
            ]))
            el.append(internal_table)

    doc.build(el, canvasmaker=_make_canvas_class(
        _get_watermark_path(), PAGE_W, PAGE_H, MARGIN, CONTENT_W, HEADER_H
    ))

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="producao_{order.number}.pdf"'
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response