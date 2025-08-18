import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pptx import Presentation
from pptx.util import Inches, Pt  # Adicionando importação de Pt aqui
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from PIL import Image
from collections import defaultdict
from utils.excel import load_product_data, load_image_links
from utils.images import find_image_for_sku, download_image, validate_image, get_image_dimensions
from utils.logger import get_logger
from layout_config import get_layout_config  # Modificando a importação

# Definindo FONT_NAME como constante no próprio arquivo
FONT_NAME = "Calibri"

logger = get_logger(__name__)

@dataclass
class Product:
    sku: str
    name: str
    category: str
    image_url: Optional[str]
    image_path: Optional[str] = None

def add_textbox(slide, left, top, width, height, text, font_size=14, bold=False, align=PP_ALIGN.CENTER, 
                font_color=None):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = str(text) if text is not None else ""
    font = run.font
    font.size = Pt(font_size)
    font.bold = bold
    font.name = FONT_NAME
    if font_color:
        font.color.rgb = font_color
    p.alignment = align
    return box

def add_product_tile(slide, left, top, box_w, box_h, product: Product):
    titulo_h = Inches(0.45)
    nome_h = Inches(0.30)
    sku_h = Inches(0.15)
    padding = Inches(0.08)

    img_top = top + padding
    img_left = left + padding
    img_w = box_w - 2*padding
    img_h = box_h - titulo_h - 2*padding

    if product.image_path and os.path.exists(product.image_path) and validate_image(product.image_path):
        try:
            iw, ih = get_image_dimensions(product.image_path)
            scale = min(img_w/iw, img_h/ih)
            new_w = int(iw*scale)
            new_h = int(ih*scale)
            slide.shapes.add_picture(
                product.image_path,
                img_left + (img_w - new_w)/2,
                img_top + (img_h - new_h)/2,
                width=new_w, height=new_h
            )
        except Exception as e:
            logger.error(f"Erro ao adicionar imagem {product.image_path}: {str(e)}")
            add_textbox(
                slide, img_left, img_top, img_w, img_h, 
                "Imagem inválida", font_size=12
            )
    else:
        add_textbox(
            slide, img_left, img_top, img_w, img_h, 
            "Sem imagem", font_size=12
        )

    add_textbox(
        slide, left + padding, top + box_h - titulo_h, 
        box_w - 2*padding, nome_h, product.name, 
        font_size=14, bold=True
    )
    
    sku_box = add_textbox(
        slide, left + padding, top + box_h - sku_h - padding/2, 
        box_w - 2*padding, sku_h, f"SKU: {product.sku}", 
        font_size=12, font_color=RGBColor(90, 90, 90)
)

def add_category_title(slide, title_text):
    left, top = Inches(0.4), Inches(0.3)
    box = slide.shapes.add_textbox(left, top, Inches(10.0), Inches(0.6))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = str(title_text)
    font = run.font
    font.size = Pt(28)
    font.bold = True
    font.name = FONT_NAME
    p.alignment = PP_ALIGN.LEFT

def process_products(df, c_sku, c_nome, c_cat, c_img, imagens_dir, skip_download=False) -> List[Product]:
    products = []
    for _, row in df.iterrows():
        sku = str(row[c_sku]).strip()
        product = Product(
            sku=sku,
            name=str(row[c_nome]).strip(),
            category=str(row[c_cat]).strip(),
            image_url=str(row["FinalImageURL"]).strip() if row["FinalImageURL"] else None
        )
        
        # Verifica se a imagem já existe localmente
        product.image_path = find_image_for_sku(sku, imagens_dir, product.image_url)
        
        # Se não existe e não devemos pular o download, tenta baixar
        if not product.image_path and product.image_url and not skip_download:
            logger.info(f"Baixando imagem para SKU {sku}...")
            product.image_path = download_image(product.image_url, sku, imagens_dir)
        
        products.append(product)
    
    return products

def build_catalog(args, layout_config):
    logger.info("Iniciando geração do catálogo...")
    
    # 1. Carrega dados
    df, c_sku, c_nome, c_cat, c_img = load_product_data(args.excel)
    logger.info(f"Planilha de produtos carregada com {len(df)} itens.")
    
    img_links_df = load_image_links(args.img_excel)
    logger.info(f"Planilha de links de imagens carregada com {len(img_links_df)} registros.")

    # 2. Mescla dados
    df = df.merge(img_links_df, how="left", left_on=c_sku, right_on="SKU")
    logger.debug("Mesclagem concluída entre produtos e links de imagem.")

    # 3. Define URL final da imagem
    if c_img:
        df["FinalImageURL"] = df[c_img].fillna(df["ImageURL"])
    else:
        df["FinalImageURL"] = df["ImageURL"]

    # 4. Limita produtos se necessário
    if args.max_products > 0:
        df = df.head(args.max_products)
        logger.info(f"Limitado a {args.max_products} produtos")

    # 5. Processa produtos
    products = process_products(df, c_sku, c_nome, c_cat, c_img, args.imagens, args.skip_download)
    products = [p for p in products if p.image_path or args.include_no_image]
    
    # 6. Ordena produtos
    products.sort(key=lambda x: (x.category, x.name, x.sku))
    logger.info("Produtos ordenados por categoria/nome/SKU.")

    # 7. Agrupa por categoria
    categories = defaultdict(list)
    for product in products:
        categories[product.category].append(product)

    # 8. Prepara apresentação
    prs = Presentation(r"C:\Users\gustavo\Documents\Automation project\template\template_catalogo.ppxt")
    logger.info("Template PPTX carregado.")
    blank_layout = prs.slide_layouts[6]

    # 9. Calcula dimensões do grid
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    grid_w = slide_w - 2*layout_config['MARGEM']
    grid_h = slide_h - layout_config['TOPO'] - layout_config['BASE']
    box_w = (grid_w - (layout_config['GRID_COLS']-1)*layout_config['HGAP']) / layout_config['GRID_COLS']
    box_h = (grid_h - (layout_config['GRID_ROWS']-1)*layout_config['VGAP']) / layout_config['GRID_ROWS']

    # 10. Gera slides
    for category, cat_products in categories.items():
        logger.info(f"Criando slides para categoria: {category} ({len(cat_products)} itens)")
        
        tile_index = 0
        while tile_index < len(cat_products):
            slide = prs.slides.add_slide(blank_layout)
            add_category_title(slide, category)
            
            for r in range(layout_config['GRID_ROWS']):
                for c in range(layout_config['GRID_COLS']):
                    if tile_index >= len(cat_products):
                        break
                    
                    product = cat_products[tile_index]
                    left = layout_config['MARGEM'] + c*(box_w + layout_config['HGAP'])
                    top = layout_config['TOPO'] + r*(box_h + layout_config['VGAP'])
                    
                    add_product_tile(slide, left, top, box_w, box_h, product)
                    tile_index += 1

    # 11. Salva apresentação
    prs.save(args.out)
    logger.info(f"Catálogo gerado com sucesso: {args.out}")