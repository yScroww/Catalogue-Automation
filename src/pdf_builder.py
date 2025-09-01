import os
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer,
    Image, Paragraph, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from PIL import Image as PilImage

from .utils.logger import get_logger

logger = get_logger(__name__)

# -------------------------
# Configurações globais
# -------------------------
MARGIN = 0.4 * inch
styles = getSampleStyleSheet()
ORANGE_COLOR = colors.Color(red=(240/255), green=(132/255), blue=0)

# -------------------------
# Estilos de texto
# -------------------------
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
# Funções auxiliares
# -------------------------

def resize_dimensions_to_frame(img_path: str, max_width: float, max_height: float):
    """
    Calcula as novas dimensões de uma imagem para caber em um frame.
    """
    try:
        with PilImage.open(img_path) as im:
            img_width, img_height = im.size
    except Exception:
        logger.error(f"Não foi possível ler as dimensões da imagem: {img_path}")
        return max_width, max_height

    scale = min(max_width / img_width, max_height / img_height)
    new_width = img_width * scale
    new_height = img_height * scale
    logger.debug(f"Redimensionando imagem de {img_width}x{img_height} para {new_width:.1f}x{new_height:.1f} pt")
    return new_width, new_height

def create_product_cell(product, col_width):
    """
    Cria célula de tabela para um produto com altura fixa (texto + imagem).
    """
    img_path = product.get('image_path')
    text_height = 0.45 * inch
    image_size = col_width * 0.9

    cell_content = []

    # Bloco com nome e SKU
    name_and_sku = Table(
        [
            [Paragraph(product.get('Nome do Produto', 'N/A'), product_name_style)],
            [Paragraph(f"SKU: {product.get('SKU', 'N/A')}", sku_style)]
        ],
        colWidths=[col_width],
        rowHeights=[text_height/2, text_height/2],
        style=TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ])
    )
    cell_content.append(name_and_sku)

    # Bloco da imagem
    if img_path and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
        try:
            img_width, img_height = resize_dimensions_to_frame(img_path, image_size, image_size)
            img = Image(img_path, width=img_width, height=img_height)
            img.hAlign = 'CENTER'
            cell_content.append(img)
        except Exception:
            cell_content.append(Paragraph("Imagem não disponível", normal_style))
    else:
        cell_content.append(Paragraph("Imagem não disponível", normal_style))

    final_cell_table = Table(
        [[c] for c in cell_content],
        colWidths=[col_width],
        style=TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ])
    )
    return final_cell_table


def create_catalog_pdf(products: list, output_path: str, cover_path: str = 'data/capas_forças'):
    logger.info(f"Iniciando criação do PDF '{output_path}'")
    logger.info(f"Usando o caminho para capas: '{cover_path}'")

    doc = SimpleDocTemplate(
        output_path,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        pagesize=A4
    )
    story = []
    
    # Tamanho interno da página (sem margens)
    page_width, page_height = A4
    max_width = page_width - (doc.leftMargin + doc.rightMargin)
    max_height = page_height - (doc.topMargin + doc.bottomMargin)
    
    # Adicionando log para a quantidade de produtos recebidos
    logger.info(f"Lista de produtos recebida. Total: {len(products)}.")

    # Agrupar produtos: Força > Grupo > Família
    all_products_by_force = {}
    for product in products:
        force_name = product.get('Nome da Força', 'Outros')
        group = product.get('Grupo', 'Não Classificado')
        family = product.get('Familia', 'Não Classificada')
        all_products_by_force.setdefault(force_name, {}).setdefault(group, {}).setdefault(family, []).append(product)
        
    # Adicionando log para o dicionário de agrupamento
    logger.info(f"Produtos agrupados por força: {list(all_products_by_force.keys())}")

    force_order = ['Food', 'Bebidas', 'Garoto', 'Purina', 'Nestlé']
    col_width = doc.width / 4.0

    # Capa inicial
    capa_path = os.path.join(cover_path, 'capa.png')
    if os.path.exists(capa_path):
        try:
            img_width, img_height = resize_dimensions_to_frame(capa_path, max_width, max_height)
            capa_img = Image(capa_path, width=img_width, height=img_height)
            capa_img.hAlign = 'CENTER'
            story.append(capa_img)
            story.append(PageBreak())
            logger.info("Capa inicial adicionada com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao adicionar capa inicial: {e}")
    else:
        logger.warning("Capa inicial não encontrada.")
        story.append(Paragraph("Capa inicial não disponível", styles['h1']))
        story.append(PageBreak())

    # Loop pelas forças
    for force_name in force_order:
        if force_name not in all_products_by_force:
            logger.warning(f"Nenhum produto encontrado para a força '{force_name}'. Ignorando.")
            continue

        # Adicionando log para a força atual
        logger.info(f"Processando força: '{force_name}'.")

        # Capa por força
        force_capa_path = os.path.join(cover_path, f'{force_name.lower()}.png')
        if os.path.exists(force_capa_path):
            try:
                img_width, img_height = resize_dimensions_to_frame(force_capa_path, max_width, max_height)
                force_capa_img = Image(force_capa_path, width=img_width, height=img_height)
                force_capa_img.hAlign = 'CENTER'
                story.append(force_capa_img)
                story.append(PageBreak())
                logger.info(f"Capa da força '{force_name}' adicionada com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao adicionar capa da força '{force_name}': {e}")
        else:
            logger.warning(f"Capa da força '{force_name}' não encontrada.")

        groups = all_products_by_force[force_name]
        for group_name, families in groups.items():
            story.append(Spacer(1, 0.25 * inch))
            group_title = Paragraph(str(group_name), group_heading_style)
            group_table = Table([[group_title]], colWidths=[doc.width])
            group_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), ORANGE_COLOR),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))

            # Combinar famílias pequenas
            families_to_process = list(families.items())
            combined_families_list = []
            i = 0
            while i < len(families_to_process):
                family_name, family_products = families_to_process[i]
                combined_products = list(family_products)
                combined_name = str(family_name)
                if len(combined_products) <= 2 and i + 1 < len(families_to_process):
                    next_family_name, next_family_products = families_to_process[i+1]
                    if len(next_family_products) <= (4 - len(combined_products)):
                        combined_name += f" & {str(next_family_name)}"
                        combined_products.extend(next_family_products)
                        i += 1
                combined_families_list.append((combined_name, combined_products))
                i += 1

            # Primeira família junto do título do grupo
            group_and_first_family = [group_table, Spacer(1, 0.05 * inch)]
            if combined_families_list:
                first_family_name, first_family_products = combined_families_list[0]
                product_cells = [create_product_cell(p, col_width) for p in first_family_products]
                table_rows = []
                for k in range(0, len(product_cells), 4):
                    row = product_cells[k:k+4]
                    while len(row) < 4:
                        row.append(Spacer(1,1))
                    table_rows.append(row)

                if table_rows:
                    family_title = Paragraph(str(first_family_name), family_heading_style)
                    first_row_table = Table([table_rows[0]], colWidths=[col_width]*4, hAlign='LEFT')
                    first_row_table.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                        ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('TOPPADDING', (0,0), (-1,-1), 0),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ]))
                    group_and_first_family.extend([family_title, first_row_table])
                    story.append(KeepTogether(group_and_first_family))
                    
                    # Adicionando log para a primeira família do grupo
                    logger.info(f"Adicionando primeira família '{first_family_name}' com {len(first_family_products)} produtos.")

                    for remaining_row in table_rows[1:]:
                        grid_table = Table([remaining_row], colWidths=[col_width]*4, hAlign='LEFT')
                        grid_table.setStyle(TableStyle([
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('LEFTPADDING', (0,0), (-1,-1), 0),
                            ('RIGHTPADDING', (0,0), (-1,-1), 0),
                            ('TOPPADDING', (0,0), (-1,-1), 0),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                        ]))
                        story.append(grid_table)

            # Demais famílias
            for family_name, family_products in combined_families_list[1:]:
                story.append(Spacer(1, 0.1 * inch))
                family_content = [
                    Paragraph(str(family_name), family_heading_style),
                    Spacer(1, 0.05 * inch)
                ]
                product_cells = [create_product_cell(p, col_width) for p in family_products]
                table_data = []
                for k in range(0, len(product_cells), 4):
                    row = product_cells[k:k+4]
                    while len(row) < 4:
                        row.append(Spacer(1,1))
                    table_data.append(row)
                if table_data:
                    family_content.append(Table([table_data[0]], colWidths=[col_width]*4, hAlign='LEFT'))
                story.append(KeepTogether(family_content))
                
                # Adicionando log para as demais famílias
                logger.info(f"Adicionando família '{family_name}' com {len(family_products)} produtos.")

                for remaining_row in table_data[1:]:
                    grid_table = Table([remaining_row], colWidths=[col_width]*4, hAlign='LEFT')
                    grid_table.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                        ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('TOPPADDING', (0,0), (-1,-1), 0),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ]))
                    story.append(grid_table)

            story.append(Spacer(1, 0.1 * inch))
            logger.info(f"Adicionados produtos do Grupo '{group_name}'")

    # Adicionando log final antes de construir o PDF
    logger.info(f"Construindo PDF com {len(story)} elementos na história.")

    try:
        doc.build(story)
        logger.info(f"Catálogo criado com sucesso: '{output_path}'")
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise