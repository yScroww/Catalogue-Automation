import os
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image, Paragraph, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from .utils.logger import get_logger

logger = get_logger(__name__)

# Configurações globais
MARGIN = 0.4 * inch
styles = getSampleStyleSheet()
ORANGE_COLOR = colors.Color(red=(240/255), green=(132/255), blue=0)

# Estilos de texto
group_heading_style = ParagraphStyle(
    'GroupHeading', parent=styles['h1'],
    fontName='Helvetica-Bold', fontSize=16,
    textColor=colors.white, alignment=TA_CENTER, spaceAfter=4
)
family_heading_style = ParagraphStyle(
    'FamilyHeading', parent=styles['h2'],
    fontName='Helvetica-Bold', fontSize=14,
    textColor=ORANGE_COLOR, alignment=TA_CENTER,
    spaceBefore=6, spaceAfter=3
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

def create_product_cell(product, col_width):
    """
    Cria célula de tabela para um produto com altura fixa (texto + imagem).
    """
    img_path = product.get('image_path')
    text_height = 0.45 * inch
    image_size = col_width * 0.9

    cell_content = []

    # Bloco com nome e SKU
    name_and_sku = Table([
        [Paragraph(product.get('Nome do Produto', 'N/A'), product_name_style)],
        [Paragraph(f"SKU: {product.get('SKU', 'N/A')}", sku_style)]
    ], colWidths=[col_width],
        rowHeights=[text_height/2, text_height/2],
        style=TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ]))
    cell_content.append(name_and_sku)

    # Bloco da imagem
    if img_path and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
        try:
            img = Image(img_path, width=image_size, height=image_size)
            img.hAlign = 'CENTER'
            cell_content.append(img)
        except Exception:
            cell_content.append(Paragraph("Imagem não disponível", normal_style))
    else:
        cell_content.append(Paragraph("Imagem não disponível", normal_style))

    final_cell_table = Table([[c] for c in cell_content],
                            colWidths=[col_width],
                            style=TableStyle([
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                                ('LEFTPADDING', (0,0), (-1,-1), 0),
                                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                                ('TOPPADDING', (0,0), (-1,-1), 0),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                            ]))
    return final_cell_table

def create_catalog_pdf(products: list, output_path: str):
    logger.info(f"Iniciando criação do PDF '{output_path}'")

    doc = SimpleDocTemplate(output_path,
                            rightMargin=MARGIN, leftMargin=MARGIN,
                            topMargin=MARGIN, bottomMargin=MARGIN)
    story = []
    all_products_by_group = {}

    # Agrupa por grupo/familia
    for product in products:
        group = product.get('Grupo', 'Não Classificado')
        family = product.get('Familia', 'Não Classificada')
        all_products_by_group.setdefault(group, {}).setdefault(family, []).append(product)

    col_width = doc.width / 4.0

    # Itera sobre os grupos
    is_first_group = True
    for group_name, families in all_products_by_group.items():
        # Adiciona o cabeçalho do grupo. Se for o primeiro, não adiciona espaço. Se não for, adiciona um espaço maior.
        if not is_first_group:
            story.append(Spacer(1, 0.4 * inch))
        is_first_group = False
        
        group_title = Paragraph(str(group_name), group_heading_style)
        group_table = Table([[group_title]], colWidths=[doc.width])
        group_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ORANGE_COLOR),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(group_table)
        story.append(Spacer(1, 0.15 * inch))

        # Novo loop para processar as famílias, combinando as pequenas
        families_to_process = list(families.items())
        i = 0
        while i < len(families_to_process):
            family_name, family_products = families_to_process[i]
            combined_products = list(family_products)
            combined_name = str(family_name)
            
            # Combina famílias pequenas (1 ou 2 produtos) com a próxima, se ela também for pequena
            if len(combined_products) <= 2 and i + 1 < len(families_to_process) and len(families_to_process[i+1][1]) <= (4-len(combined_products)):
                next_family_name, next_family_products = families_to_process[i+1]
                combined_name += f" & {str(next_family_name)}"
                combined_products.extend(next_family_products)
                i += 1

            # Divide os produtos em linhas de 4
            product_cells = [create_product_cell(p, col_width) for p in combined_products]
            table_rows = []
            for k in range(0, len(product_cells), 4):
                row = product_cells[k:k+4]
                while len(row) < 4:
                    row.append(Spacer(1,1))
                table_rows.append(row)

            # Adiciona o título e a primeira linha da tabela juntos para evitar a quebra
            if table_rows:
                family_title_and_first_row = [
                    Paragraph(combined_name, family_heading_style),
                    Spacer(1, 0.1 * inch),
                    Table([table_rows[0]], colWidths=[col_width]*4, hAlign='LEFT', style=TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                        ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('TOPPADDING', (0,0), (-1,-1), 0),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ]))
                ]
                story.append(KeepTogether(family_title_and_first_row))

                # Adiciona o restante das linhas da tabela sem o KeepTogether
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

            story.append(Spacer(1, 0.2 * inch))
            
            logger.info(f"Adicionados {len(combined_products)} produtos da(s) Família(s) '{combined_name}'")
            i += 1
            
    try:
        doc.build(story)
        logger.info(f"Catálogo criado com sucesso: '{output_path}'")
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise