# src/pdf_builder.py
import os
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer,
    Image as RLImage, Paragraph, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from PIL import Image as PilImage

from .utils.logger import get_logger

logger = get_logger(__name__)

MARGIN = 0.4 * inch
styles = getSampleStyleSheet()
ORANGE_COLOR = colors.Color(red=(240/255), green=(132/255), blue=0)

# Estilos
group_heading_style = ParagraphStyle(
    'GroupHeading', parent=styles['h1'],
    fontName='Helvetica-Bold', fontSize=16,
    textColor=colors.white, alignment=TA_CENTER, spaceAfter=2
)
family_heading_style = ParagraphStyle(
    'FamilyHeading', parent=styles['h2'],
    fontName='Helvetica-Bold', fontSize=14,
    textColor=ORANGE_COLOR, alignment=TA_CENTER,
    spaceBefore=4, spaceAfter=1
)
product_name_style = ParagraphStyle(
    'ProductName', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=8,
    leading=9, alignment=TA_CENTER
)
sku_style = ParagraphStyle(
    'SKUStyle', parent=styles['Normal'],
    fontName='Helvetica', fontSize=7,
    leading=8, alignment=TA_CENTER, textColor=colors.grey
)
normal_style = ParagraphStyle(
    'NormalStyle', parent=styles['Normal'],
    fontName='Helvetica', fontSize=8,
    leading=10, alignment=TA_CENTER
)

# -------------------------
# Utilitários
# -------------------------
def clamp_cover_dimensions(img_path: str, max_w: float, max_h: float) -> tuple[float, float]:
    """
    Retorna width,height (pt) para a imagem de capa ajustada ao frame.
    Usa dimensões em pixels e aplica escala para caber no frame (pt).
    """
    try:
        with PilImage.open(img_path) as im:
            w_px, h_px = im.size
    except Exception:
        logger.debug(f"Falha ao ler capa para redimensionar: {img_path}")
        # fallback simples
        return max_w, max_h

    # scale relative to pixels -> treat px as "unit" then scale to points
    scale = min(max_w / w_px, max_h / h_px, 1.0)
    return (w_px * scale, h_px * scale)

def make_table_style():
    return TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ])

# -------------------------
# Cell / Grid
# -------------------------
def create_product_cell(product: dict, col_width: float, image_size_pt: float, text_height_pt: float):
    """
    Cria uma célula uniforme: uma tabela com (nome+sku) e imagem.
    image_size_pt = largura/altura desejada em pontos para a imagem.
    text_height_pt = área reservada para nome+sku.
    """
    try:
        img_path = product.get('image_path')
        cell_parts = []

        # nome + sku
        name_sku = Table(
            [
                [Paragraph(product.get('Nome do Produto', 'N/A'), product_name_style)],
                [Paragraph(f"SKU: {product.get('SKU', 'N/A')}", sku_style)]
            ],
            colWidths=[col_width],
            rowHeights=[text_height_pt/2, text_height_pt/2],
            style=TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                ('TOPPADDING', (0,0), (-1,-1), 1),
            ])
        )
        cell_parts.append(name_sku)

        # imagem: usamos sempre image_size_pt x image_size_pt (uniforme)
        if img_path and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
            try:
                img = RLImage(img_path, width=image_size_pt, height=image_size_pt)
                img.hAlign = 'CENTER'
                cell_parts.append(img)
            except Exception as e:
                logger.warning(f"Falha ao inserir imagem do produto {product.get('SKU')}: {e}")
                cell_parts.append(Paragraph("Imagem não disponível", normal_style))
        else:
            cell_parts.append(Paragraph("Imagem não disponível", normal_style))

        # tabela final da célula (uma coluna, empilha textos + imagem)
        final = Table([[p] for p in cell_parts],
                      colWidths=[col_width],
                      style=make_table_style())
        return final
    except Exception as e:
        logger.error(f"Erro ao construir célula de produto (SKU={product.get('SKU')}): {e}")
        # placeholder simples para não abortar o documento
        return Table([[Paragraph("Erro produto", normal_style)]], colWidths=[col_width], style=make_table_style())

# -------------------------
# Função principal
# -------------------------
def create_catalog_pdf(products: list, output_path: str, cover_path: str = 'data/capas_forças'):
    logger.info(f"Iniciando criação do PDF '{output_path}'")
    doc = SimpleDocTemplate(
        output_path,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        pagesize=A4
    )
    story = []

    page_w, page_h = A4
    max_w = page_w - (doc.leftMargin + doc.rightMargin)
    max_h = page_h - (doc.topMargin + doc.bottomMargin)

    logger.info(f"Total produtos recebidos: {len(products)}")

    # agrupar Força -> Grupo -> Família
    by_force = {}
    for p in products:
        force = p.get('Nome da Força', 'Outros')
        group = p.get('Grupo', 'Não Classificado')
        fam = p.get('Familia', 'Não Classificada')
        by_force.setdefault(force, {}).setdefault(group, {}).setdefault(fam, []).append(p)

    logger.info(f"Forças encontradas: {list(by_force.keys())}")

    # largura de coluna em pontos
    col_width = doc.width / 4.0

    # Capa inicial (ajusta dimensões para não exceder frame)
    capa_path = os.path.join(cover_path, 'capa.png')
    if os.path.exists(capa_path):
        try:
            w_pt, h_pt = clamp_cover_dimensions(capa_path, max_w, max_h)
            img = RLImage(capa_path, width=w_pt, height=h_pt)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(PageBreak())
            logger.info("Capa inicial adicionada.")
        except Exception as e:
            logger.error(f"Erro ao adicionar capa inicial: {e}")
    else:
        logger.warning("Capa inicial não encontrada.")
        story.append(Paragraph("Capa inicial não disponível", styles['h1']))
        story.append(PageBreak())

    # cores e ordem das forças
    force_order = ['Food', 'Bebidas', 'Garoto', 'Purina', 'Nestlé']

    for force_name in force_order:
        if force_name not in by_force:
            logger.debug(f"Força '{force_name}' sem produtos — pulando.")
            continue

        # capa da força
        force_capa = os.path.join(cover_path, f"{force_name.lower()}.png")
        if os.path.exists(force_capa):
            try:
                w_pt, h_pt = clamp_cover_dimensions(force_capa, max_w, max_h)
                img = RLImage(force_capa, width=w_pt, height=h_pt)
                img.hAlign = 'CENTER'
                story.append(img)
                story.append(PageBreak())
                logger.info(f"Capa da força '{force_name}' adicionada.")
            except Exception as e:
                logger.error(f"Erro ao adicionar capa da força '{force_name}': {e}")

        groups = by_force[force_name]
        for group_name, families in groups.items():
            # título do grupo
            story.append(Spacer(1, 0.2 * inch))
            group_title = Paragraph(str(group_name), group_heading_style)
            group_table = Table([[group_title]], colWidths=[doc.width])
            group_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), ORANGE_COLOR),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))

            # combine famílias pequenas (mesma lógica)
            fam_items = list(families.items())
            combined = []
            i = 0
            while i < len(fam_items):
                fname, fprods = fam_items[i]
                prods_comb = list(fprods)
                name_comb = str(fname)
                if len(prods_comb) <= 2 and i+1 < len(fam_items):
                    next_name, next_prods = fam_items[i+1]
                    if len(next_prods) <= (4 - len(prods_comb)):
                        name_comb += f" & {next_name}"
                        prods_comb.extend(next_prods)
                        i += 1
                combined.append((name_comb, prods_comb))
                i += 1

            # renderiza primeiro family junto com título do grupo (KeepTogether)
            if combined:
                first_name, first_prods = combined[0]
                # configurações visuais: altura do texto + imagem
                text_h = 0.45 * inch
                image_size = col_width * 0.9   # largura em pontos que queremos desenhar a imagem
                # altura da célula: texto + imagem + pequeno espaçamento
                row_height = text_h + image_size + 4  # 4 pt de folga

                # Cria células uniformes
                product_cells = [create_product_cell(p, col_width, image_size_pt=image_size, text_height_pt=text_h) for p in first_prods]
                # agrupa em linhas de 4
                rows = []
                for k in range(0, len(product_cells), 4):
                    row = product_cells[k:k+4]
                    while len(row) < 4:
                        row.append(Spacer(1,1)) # type: ignore
                    rows.append(row)

                # Bloco grupo + primeira familia
                block = [group_table, Spacer(1, 0.05 * inch), Paragraph(str(first_name), family_heading_style)]
                if rows:
                    try:
                        first_table = Table([rows[0]], colWidths=[col_width]*4, rowHeights=[row_height], hAlign='LEFT', style=make_table_style())
                        block.append(first_table)
                    except Exception as e:
                        logger.error(f"Erro ao montar primeira tabela da família '{first_name}': {e}")
                        block.append(Paragraph("Erro ao montar family table", normal_style))
                story.append(KeepTogether(block))

                # restantes linhas da primeira familia
                for r in rows[1:]:
                    try:
                        t = Table([r], colWidths=[col_width]*4, rowHeights=[row_height], hAlign='LEFT', style=make_table_style())
                        story.append(t)
                    except Exception as e:
                        logger.error(f"Erro ao adicionar linha da família '{first_name}': {e}")

            # Demais familias
            for fam_name, fam_prods in combined[1:]:
                story.append(Spacer(1, 0.08 * inch))
                family_block = [Paragraph(str(fam_name), family_heading_style), Spacer(1, 0.05 * inch)]

                text_h = 0.45 * inch
                image_size = col_width * 0.9
                row_height = text_h + image_size + 4

                product_cells = [create_product_cell(p, col_width, image_size_pt=image_size, text_height_pt=text_h) for p in fam_prods]
                rows = []
                for k in range(0, len(product_cells), 4):
                    row = product_cells[k:k+4]
                    while len(row) < 4:
                        row.append(Spacer(1,1)) # type: ignore
                    rows.append(row)

                if rows:
                    try:
                        first_table = Table([rows[0]], colWidths=[col_width]*4, rowHeights=[row_height], hAlign='LEFT', style=make_table_style())
                        family_block.append(first_table)
                    except Exception as e:
                        logger.error(f"Erro montar family first table '{fam_name}': {e}")
                        family_block.append(Paragraph("Erro ao montar family table", normal_style))

                story.append(KeepTogether(family_block))

                for r in rows[1:]:
                    try:
                        t = Table([r], colWidths=[col_width]*4, rowHeights=[row_height], hAlign='LEFT', style=make_table_style())
                        story.append(t)
                    except Exception as e:
                        logger.error(f"Erro ao adicionar linha da família '{fam_name}': {e}")

            story.append(Spacer(1, 0.1 * inch))
            logger.info(f"Grupo '{group_name}' adicionado com {len(families)} famílias.")

    logger.info(f"Total flowables a construir: {len(story)}")
    try:
        doc.build(story)
        logger.info(f"PDF criado: {output_path}")
    except Exception as e:
        logger.error(f"Erro ao construir PDF: {e}")
        raise
