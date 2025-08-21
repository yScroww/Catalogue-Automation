import os
import math
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer, Image as RLImage,
    Paragraph, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from .utils.logger import get_logger

logger = get_logger(__name__)

# Configurações globais
MARGIN = 0.5 * inch
styles = getSampleStyleSheet()

# Cores e Estilos
ORANGE_COLOR = colors.Color(red=(240/255), green=(132/255), blue=(0/255))

# Estilos personalizados para o novo layout
group_heading_style = ParagraphStyle(
    'GroupHeading',
    parent=styles['h1'],
    fontName='Helvetica-Bold',
    fontSize=16,
    textColor=colors.white,
    alignment=TA_CENTER,
    spaceAfter=5
)
family_heading_style = ParagraphStyle(
    'FamilyHeading',
    parent=styles['h2'],
    fontName='Helvetica-Bold',
    fontSize=14,
    textColor=ORANGE_COLOR,
    spaceBefore=10,
    spaceAfter=5,
    alignment=TA_CENTER
)
product_name_style = ParagraphStyle(
    'ProductName',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=8,
    leading=10,
    alignment=TA_CENTER
)
sku_style = ParagraphStyle(
    'SKUStyle',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=7,
    leading=9,
    alignment=TA_CENTER,
    textColor=colors.grey
)
normal_style = ParagraphStyle(
    'NormalStyle',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=9,
    leading=11,
    alignment=TA_CENTER
)

def create_product_cell(product, col_width):
    """
    Cria uma célula de tabela com as informações de um produto,
    garantindo alinhamento e espaçamento fixo.
    """
    img_path = product.get('image_path')
    
    # Altura fixa para a caixa de texto (nome + SKU)
    text_height = 0.6 * inch
    # Tamanho quadrado para a imagem (as imagens já chegam 800x800)
    image_size = col_width * 0.95

    cell_content = []

    # 1) Nome e SKU
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
    cell_content.append(Spacer(1, 0.04 * inch))

    # 2) Imagem (já quadrada e padronizada)
    if img_path and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
        try:
            img = RLImage(img_path, width=image_size, height=image_size)
            img.hAlign = 'CENTER'
            cell_content.append(img)
        except Exception:
            cell_content.append(Paragraph("Imagem não disponível", normal_style))
    else:
        cell_content.append(Paragraph("Imagem não disponível", normal_style))
    
    # Tabela final da célula
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

def create_catalog_pdf(products: list, output_path: str):
    """
    Cria um catálogo em PDF com layout de grade 4x4.
    """
    logger.info(f"Iniciando a criação do PDF em '{output_path}' com layout 4x4.")

    doc = SimpleDocTemplate(
        output_path, 
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
    )
    
    story = []
    
    # Agrupa os produtos por Grupo e Família
    all_products_by_group = {}
    for product in products:
        group = product.get('Grupo', 'Produto Sem Grupo')
        family = product.get('Família', 'Sem Família')
        all_products_by_group.setdefault(group, {}).setdefault(family, []).append(product)

    # Largura da coluna para a grade de produtos
    col_width = (doc.width) / 4.0

    for group_name, families in all_products_by_group.items():
        if story:
            story.append(PageBreak())

        # Título do Grupo
        group_title = Paragraph(str(group_name), group_heading_style)
        group_table = Table([[group_title]], colWidths=[doc.width])
        group_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ORANGE_COLOR),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(group_table)
        story.append(Spacer(1, 0.25 * inch))

        for family_name, family_products in families.items():
            # Cabeçalho da família
            story.append(Paragraph(str(family_name), family_heading_style))
            story.append(Spacer(1, 0.1 * inch))
            
            # Divide os produtos em linhas de 4
            product_cells = [create_product_cell(p, col_width) for p in family_products]
            table_data = []
            for k in range(0, len(product_cells), 4):
                row = product_cells[k:k+4]
                while len(row) < 4:
                    row.append(Spacer(1,1))
                table_data.append(row)
                
            grid_table = Table(
                table_data,
                colWidths=[col_width] * 4,
                hAlign='CENTER',  # centraliza a grade
                style=TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LEFTPADDING', (0,0), (-1,-1), 2),
                    ('RIGHTPADDING', (0,0), (-1,-1), 2),
                    ('TOPPADDING', (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ])
            )
            story.append(grid_table)
            story.append(Spacer(1, 0.25 * inch))
            
            logger.info(f"Adicionados {len(family_products)} produtos da Família '{family_name}'.")

    try:
        doc.build(story)
        logger.info(f"Catálogo criado com sucesso em '{output_path}'.")
    except Exception as e:
        logger.error(f"Erro ao construir o PDF: {e}")
        raise
