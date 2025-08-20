import os
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from .utils.logger import get_logger

logger = get_logger(__name__)

# Configurações globais
MARGIN = 0.5 * inch
IMAGE_WIDTH_PDF = 1.5 * inch
styles = getSampleStyleSheet()

# Estilos
group_heading_style = ParagraphStyle(
    'GroupHeading',
    parent=styles['h1'],
    spaceBefore=20,
    spaceAfter=6,
    alignment=TA_CENTER
)
sku_style = ParagraphStyle(
    'SKUStyle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=10,
    leading=12
)
normal_style = ParagraphStyle(
    'NormalStyle',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=10,
    leading=12
)

def create_catalog_pdf(products: list, output_path: str):
    """
    Cria um catálogo em PDF de forma incremental, gerenciando o fluxo
    para evitar problemas de memória e de quebra de página.
    """
    logger.info(f"Iniciando a criação do PDF incrementalmente em '{output_path}'...")
    
    doc = SimpleDocTemplate(output_path, 
                            rightMargin=MARGIN,
                            leftMargin=MARGIN,
                            topMargin=MARGIN,
                            bottomMargin=MARGIN)
    
    story = []
    
    last_group = None
    
    for product in products:
        current_group = product.get('Grupo')
        if current_group != last_group:
            story.append(Spacer(1, 0.25 * inch))
            story.append(Paragraph(str(current_group), group_heading_style))
            story.append(Spacer(1, 0.1 * inch))
            last_group = current_group

        # Tenta adicionar a imagem se existir e for um arquivo válido
        img_path = product.get('image_path')
        if img_path and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
            try:
                img = Image(img_path, width=IMAGE_WIDTH_PDF, height=IMAGE_WIDTH_PDF)
                img.hAlign = 'CENTER'
            except Exception as e:
                logger.error(f"Não foi possível carregar a imagem para o SKU {product['SKU']}. O arquivo pode estar corrompido ou em um formato inválido: {e}")
                img = Paragraph("Imagem não disponível", normal_style)
        else:
            img = Paragraph("Imagem não disponível", normal_style)

        # Cria a tabela de conteúdo
        product_data = [
            [Paragraph("SKU:", sku_style), Paragraph(str(product.get('SKU', 'N/A')), normal_style)],
            [Paragraph("Nome:", sku_style), Paragraph(product.get('Nome do Produto', 'N/A'), normal_style)],
            [Paragraph("EAN:", sku_style), Paragraph(str(product.get('EAN', 'N/A')), normal_style)],
        ]

        table = Table(product_data, colWidths=[1.5 * inch, doc.width - 1.5 * inch])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        # Monta a estrutura de tabela para a imagem e os dados
        main_table_data = [
            [img, table]
        ]
        
        main_table = Table(main_table_data, colWidths=[2 * inch, doc.width - 2 * inch])
        main_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))

        story.append(main_table)
        story.append(Spacer(1, 0.2 * inch))
        
        # Log de sucesso para cada produto
        logger.info(f"Produto '{product.get('Nome do Produto', 'N/A')}' (SKU: {product.get('SKU', 'N/A')}) adicionado ao PDF.")

    try:
        doc.build(story)
        logger.info(f"Catálogo criado com sucesso em '{output_path}'.")
    except Exception as e:
        logger.error(f"Erro ao construir o PDF: {e}")
        raise