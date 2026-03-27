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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether,
)
from reportlab.platypus import Image as RLImage
from reportlab.pdfgen import canvas as rl_canvas
import qrcode

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

# ── CONSTANTES ───────────────────────────────────────────────
NGROK_URL  = "https://felicita-incogitable-ichnographically.ngrok-free.dev"
PAGE_W, PAGE_H = A4
MARGIN     = 6 * mm
CONTENT_W  = PAGE_W - 2 * MARGIN
HEADER_H   = 35 * mm

_WM_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'vendas', 'img', 'deco.png'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deco.png'),
]


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _get_watermark_path():
    return next((p for p in _WM_PATHS if os.path.exists(p)), None)


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
        if getattr(client, 'number',     None): street += f', {client.number}'
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
            line += f'   |   Nº Transação: {p.transaction}'
        lines.append(line)
    return '<br/>'.join(lines)


def _build_invoice_section(order, col_lbl: float, content_w: float, s: dict) -> list:
    try:
        invoice = order.invoice
    except Exception:
        return []

    col_lbl_nf = 25 * mm
    col_val_nf = content_w / 2 - col_lbl_nf

    elements = []
    elements.append(_section_title('Nota Fiscal', s))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_info_grid([
        [('Nº NF', invoice.number),
         ('Emissão', invoice.issued_at.strftime('%d/%m/%Y'))],
    ], [col_lbl_nf, col_val_nf, col_lbl_nf, col_val_nf], s))
    elements.append(Spacer(1, 4 * mm))
    return elements
# ══════════════════════════════════════════════════════════════
# ESTILOS
# ══════════════════════════════════════════════════════════════

def _styles() -> dict:
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        'company':     s('company',     fontSize=18, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=22),
        'company_sub': s('company_sub', fontSize=9,  textColor=C_PRIMARY,    fontName='Helvetica',      leading=13),
        'doc_number':  s('doc_number',  fontSize=20, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=24, alignment=TA_RIGHT),
        'doc_label':   s('doc_label',   fontSize=9,  textColor=C_PRIMARY,    fontName='Helvetica',      leading=13, alignment=TA_RIGHT),
        'section':     s('section',     fontSize=10, textColor=C_PRIMARY,    fontName='Helvetica-Bold', spaceBefore=2, spaceAfter=4, leading=12),
        'label':       ParagraphStyle('label', fontSize=10, textColor=colors.black, fontName='Helvetica-Bold', leading=11),
        'value':       ParagraphStyle('value', fontSize=9,  textColor=colors.black, fontName='Helvetica',      leading=13),
        'th':          s('th',          fontSize=9,  textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=12),
        'td':          ParagraphStyle('td',     fontSize=9.5, textColor=colors.black, fontName='Helvetica',      leading=13),
        'td_bold':     s('td_bold',     fontSize=9.5,textColor=colors.black, fontName='Helvetica-Bold', leading=13),
        'total_label': s('total_label', fontSize=9,  textColor=colors.black, fontName='Helvetica',      leading=13, alignment=TA_RIGHT),
        'total_value': s('total_value', fontSize=9,  textColor=colors.black, fontName='Helvetica-Bold', leading=13, alignment=TA_LEFT),
        'grand_label': s('grand_label', fontSize=11, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=15, alignment=TA_RIGHT),
        'grand_value': s('grand_value', fontSize=11, textColor=C_PRIMARY,    fontName='Helvetica-Bold', leading=15, alignment=TA_LEFT),
        'obs':         s('obs',         fontSize=8.5,textColor=colors.black, fontName='Helvetica',      leading=13),
        'footer':      s('footer',      fontSize=7.5,textColor=C_PRIMARY,    fontName='Helvetica',      leading=10),
        'qr_hint':     s('qr_hint',     fontSize=6.5,textColor=C_TEXT_MUTED, fontName='Helvetica',      leading=9,  alignment=TA_CENTER),
    }

# ══════════════════════════════════════════════════════════════
# COMPONENTES DE LAYOUT
# ══════════════════════════════════════════════════════════════

def _section_title(text: str, s: dict) -> Paragraph:
    return Paragraph(text.upper(), s['section'])


def _info_grid(rows: list, col_widths: list, s: dict) -> Table:
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


def _build_compact_qr(order, qr_width: float, s: dict) -> Table:
    url    = f'{NGROK_URL}/vendas/orders/{order.pk}/public/'
    qr_img = _build_qr(url, size_mm=22)

    inner = Table(
        [[qr_img], [Paragraph('escaneie o QR code', s['qr_hint'])]],
        colWidths=[qr_width],
    )
    inner.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 1), (0, 1),   2),
    ]))
    return inner


def _build_items_table(order, content_w: float, s: dict) -> list:
    items_qs     = (
        order.items
        .select_related('product__category')
        .prefetch_related('product__components__component')
        .all()
    )
    has_discount = any(item.discount > 0 for item in items_qs)

    def _th(text):
        return Paragraph(text, s['th'])

    def _th_c(text):
        return Paragraph(text, ParagraphStyle('thC', parent=s['th'], alignment=TA_CENTER))

    def _td(text):
        return Paragraph(str(text), s['td'])

    def _td_c(text):
        return Paragraph(str(text), ParagraphStyle('tdC', parent=s['td'], alignment=TA_CENTER))

    def _td_r(text, bold=False):
        return Paragraph(str(text), ParagraphStyle('tdR', parent=s['td_bold'] if bold else s['td'], alignment=TA_RIGHT))

    def _single_measures(p) -> str:
        cm_vals = [
            f'{v:g}'.replace('.', ',')
            for v in [
                getattr(p, 'length_cm',    None),
                getattr(p, 'width_cm',     None),
                getattr(p, 'diameter_cm',  None),
                getattr(p, 'depth_cm',     None),
                getattr(p, 'curvature_cm', None),
                getattr(p, 'height_cm',    None),
            ]
            if v
        ]
        parts = []
        if cm_vals:
            parts.append(' × '.join(cm_vals) + ' cm')
        if getattr(p, 'thickness_mm', None):
            parts.append(f'{p.thickness_mm} mm')
        return ' / '.join(parts) if parts else ''

    def _measures(p) -> str:
        components = list(p.components.all()) if hasattr(p, 'components') else []
        if components:
            lines = [
                f'<b>{c.component.name}:</b> {_single_measures(c.component)}'
                for c in components
                if _single_measures(c.component)
            ]
            return '<br/>'.join(lines) if lines else '—'
        return _single_measures(p) or '—'

    COL_QTD   = 8  * mm
    COL_SKU   = 20 * mm
    COL_PRICE = 26 * mm
    COL_DISC  = 20 * mm if has_discount else 0
    COL_TOTAL = 24 * mm
    COL_DESC  = content_w - COL_QTD - COL_SKU - COL_PRICE - COL_DISC - COL_TOTAL

    header_row = [_th_c('Qtd'), _th('Cod'), _th('Produto'), _th_c('Vlr. Unit.')]
    col_widths  = [COL_QTD, COL_SKU, COL_DESC, COL_PRICE]
    if has_discount:
        header_row.append(_th_c('Desconto'))
        col_widths.append(COL_DISC)
    header_row.append(_th_c('Total'))
    col_widths.append(COL_TOTAL)

    rows = [header_row]
    for item in items_qs:
        p   = item.product
        row = [
            _td_c(item.quantity),
            _td(p.sku),
            _td(p.name),
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
        ('ALIGN',          (0, 1),  (0, -1),  'CENTER'),
        ('ALIGN',          (3, 1),  (-1, -1), 'RIGHT'),
        ('LEFTPADDING',    (0, 0),  (-1, -1), 4),
        ('RIGHTPADDING',   (0, 0),  (-1, -1), 4),
        ('TOPPADDING',     (0, 1),  (-1, -1), 5),
        ('BOTTOMPADDING',  (0, 1),  (-1, -1), 5),
    ]))
    return [t]


def _build_totals_table(order, content_w: float, s: dict) -> Table:
    COL_SPACER = content_w * 0.4
    COL_LBL    = content_w * 0.35
    COL_VAL    = content_w * 0.25

    rows = []
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
        [
            Paragraph('', s['total_label']),
            Paragraph(label, s['grand_label'] if grand else s['total_label']),
            Paragraph(value, s['grand_value'] if grand else s['total_value']),
        ]
        for label, value, grand in rows
    ]

    t = Table(data, colWidths=[COL_SPACER, COL_LBL, COL_VAL])
    t.setStyle(TableStyle([
        ('VALIGN',        (0, 0),           (-1, -1),           'MIDDLE'),
        ('TOPPADDING',    (0, 0),           (-1, -1),           2),
        ('BOTTOMPADDING', (0, 0),           (-1, -1),           2),
        ('RIGHTPADDING',  (1, 0),           (1, -1),            2),
        ('LEFTPADDING',   (2, 0),           (2, -1),            4),
        ('BACKGROUND',    (1, grand_idx),   (2, grand_idx),     C_TOTAL_BG),
        ('LINEABOVE',     (1, grand_idx),   (2, grand_idx),     0.7, C_ACCENT),
        ('LINEBELOW',     (1, grand_idx),   (2, grand_idx),     0.7, C_ACCENT),
        ('TOPPADDING',    (0, grand_idx),   (-1, grand_idx),    4),
        ('BOTTOMPADDING', (0, grand_idx),   (-1, grand_idx),    4),
        ('LINEABOVE',     (1, len(rows)-1), (2, len(rows)-1),   0.4, C_BORDER),
    ]))
    return t


# ══════════════════════════════════════════════════════════════
# CANVAS COM MARCA D'ÁGUA E NUMERAÇÃO
# ══════════════════════════════════════════════════════════════

def _make_canvas_class(wm_path):
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
                    # Página 1: desenha o logo no cabeçalho normalmente
                    if wm_path:
                        self.saveState()
                        from PIL import Image as PILImage
                        with PILImage.open(wm_path) as im:
                            orig_w, orig_h = im.size
                        scale  = HEADER_H / orig_h
                        draw_w = orig_w * scale
                        draw_x = MARGIN + (CONTENT_W - draw_w) / 2
                        self.drawImage(
                            wm_path, draw_x, PAGE_H - MARGIN - HEADER_H,
                            width=draw_w, height=HEADER_H,
                            mask='auto', preserveAspectRatio=False,
                        )
                        self.restoreState()
                else:
                    # Páginas seguintes: cabeçalho simples com nome e número do pedido
                    self.saveState()
                    self.setFont('Helvetica-Bold', 9)
                    self.setFillColor(C_PRIMARY)
                    # Extrai número do pedido do título do doc (guardado no estado)
                    doc_title = self._doc.title if hasattr(self, '_doc') else ''
                    self.drawString(MARGIN, PAGE_H - MARGIN + 1 * mm, "DECORCRIL — Pedido de Venda")
                    self.setLineWidth(0.4)
                    self.setStrokeColor(C_BORDER)
                    self.line(MARGIN, PAGE_H - MARGIN - 1 * mm, PAGE_W - MARGIN, PAGE_H - MARGIN - 1 * mm)
                    self.restoreState()

                # Numeração em todas as páginas
                self.saveState()
                self.setFont('Helvetica', 7.5)
                self.setFillColor(colors.HexColor('#64748B'))
                self.drawRightString(
                    PAGE_W - MARGIN, PAGE_H - MARGIN + 2 * mm,
                    f'Página {page_num} de {total}',
                )
                self.restoreState()
                super().showPage()
            super().save()

    return WatermarkCanvas

# ══════════════════════════════════════════════════════════════
# VIEW PRINCIPAL
# ══════════════════════════════════════════════════════════════

def order_pdf(request, pk):
    order = get_object_or_404(
    Order.objects.select_related('client', 'created_by', 'invoice'),
    pk=pk
)
    client = order.client
    s      = _styles()
    now    = datetime.now(tz=zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime('%d/%m/%Y  %H:%M')

    col_lbl = 30 * mm
    col_val = CONTENT_W / 2 - col_lbl
    cw      = [col_lbl, col_val, col_lbl, col_val]

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=f"Pedido #{order.number}", author='Decorcril',
    )

    el = []  # elements

    # ── Cabeçalho ─────────────────────────────────────────────
    left_col = [
        Paragraph("DECORCRIL", s['company']),
        Spacer(1, 2 * mm),
        Paragraph("Decorcril Acrílicos e Artesanatos Ltda.", s['company_sub']),
        Paragraph("Rua Prudente de Moraes, 1327 — Suzano/SP",  s['company_sub']),
        Paragraph("CNPJ: 45.401.044/0001-61",                  s['company_sub']),
        Paragraph("WhatsApp  (11)97899-9091",                  s['company_sub']),
    ]
    right_col = [
        Paragraph("PEDIDO DE VENDA",     s['doc_label']),
        Paragraph(f"Nº {order.number}",  s['doc_number']),
        Spacer(1, 2 * mm),
        Paragraph(f"Emissão: {now}",     s['doc_label']),
    ]
    header = Table(
        [[left_col, right_col]],
        colWidths=[CONTENT_W * 0.55, CONTENT_W * 0.45],
        rowHeights=[HEADER_H],
    )
    header.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4 * mm),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4 * mm),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    el.append(header)
    el.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceBefore=3*mm, spaceAfter=4*mm))

    # ── Dados do Cliente ──────────────────────────────────────
    el.append(_section_title('Dados do Cliente', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_info_grid([
        [('Cliente',    client.name),
         ('Pedido Nº',  order.number)],
        [('CNPJ / CPF', client.document_display),
         ('Data',       order.created_at.strftime('%d/%m/%Y'))],
        [('Telefone',   client.phone_display),
         ('Situação',   order.get_status_display())],
        [('E-mail',     getattr(client, 'email',          None)),
         ('Contato',    getattr(client, 'contact_person', None))],
    ], cw, s))
    el.append(_full_width_row('Endereço', _build_address(client), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    el.append(Spacer(1, 4 * mm))

    # ── Dados Comerciais ──────────────────────────────────────
    el.append(_section_title('Dados Comerciais', s))
    el.append(Spacer(1, 2 * mm))
    el.append(_info_grid([
        [('Vendedor',       order.created_by.get_full_name() or order.created_by.username),
         ('Tipo de Venda',  order.get_sale_type_display() if order.sale_type else None)],
        [('Transportadora', getattr(order, 'carrier',       None)),
         ('Pagamento',      getattr(order, 'payment_terms', None))],
    ], cw, s))
    if order.payments.exists():
        el.append(_full_width_row('Pagamentos', _build_payments_text(order), col_lbl, CONTENT_W, s, bg=C_LIGHT_BG))
    el.append(Spacer(1, 4 * mm))

    # ── Itens do Pedido ───────────────────────────────────────
    el.append(_section_title('Itens do Pedido', s))
    el.append(Spacer(1, 2 * mm))
    el += _build_items_table(order, CONTENT_W, s)
    el.append(Spacer(1, 4 * mm))

    # ── Observações ───────────────────────────────────────────
    if order.notes:
        el.append(_section_title('Observações', s))
        el.append(Spacer(1, 2 * mm))
        obs = Table([[Paragraph(order.notes, s['obs'])]], colWidths=[CONTENT_W])
        obs.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), C_LIGHT_BG),
            ('BOX',           (0, 0), (-1, -1), 0.5, C_BORDER),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5 * mm),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 5 * mm),
            ('TOPPADDING',    (0, 0), (-1, -1), 4 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4 * mm),
        ]))
        el.append(obs)
        el.append(Spacer(1, 4 * mm))

    # ── Resumo Financeiro + QR Code ───────────────────────────
    el.append(_section_title('Resumo Financeiro', s))
    el.append(Spacer(1, 2 * mm))
    # ── Nota Fiscal ───────────────────────────────────────────
    el += _build_invoice_section(order, col_lbl, CONTENT_W, s)

    # ── Resumo Financeiro + QR Code ───────────────────────────
    el.append(_section_title('Resumo Financeiro', s))
    qr_width     = 35 * mm
    totals_width = CONTENT_W - qr_width - 5 * mm

    side_by_side = Table(
        [[_build_compact_qr(order, qr_width, s), _build_totals_table(order, totals_width, s)]],
        colWidths=[qr_width, totals_width],
    )
    side_by_side.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    el.append(KeepTogether(side_by_side))

    doc.build(el, canvasmaker=_make_canvas_class(_get_watermark_path()))

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="pedido_{order.number}.pdf"'
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response