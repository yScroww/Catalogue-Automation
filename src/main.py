import argparse
import pandas as pd
import logging
import os
from src.pdf_builder import create_catalog_pdf
from src.utils.logger import get_logger
from src.utils.excel import load_product_data, load_image_links
from src.utils.images import find_image_for_sku, download_image, optimize_image, auto_crop_image

logger = get_logger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Gerador de Catálogo em PDF",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--excel", default="data/produtos.xlsx")
    parser.add_argument("--img-excel", default="data/base_imagens.xlsx")
    parser.add_argument("--imagens", default="data/imagens")
    parser.add_argument("--template", default=None)
    parser.add_argument("--out", type=str, default="catalogo_gerado.pdf")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--include-no-image", action="store_true")
    parser.add_argument("--max-products", type=int, default=0)
    parser.add_argument("--layout", help=argparse.SUPPRESS)
    parser.add_argument("--cols", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--rows", type=int, help=argparse.SUPPRESS)
    return parser.parse_args()

def main():
    try:
        args = parse_args()
        logger.info("Iniciando geração do catálogo em PDF...")
        
        # 1. Carrega dados principais
        df, c_sku, c_nome, c_cat, c_img = load_product_data(args.excel)
        logger.info(f"Planilha de produtos carregada com {len(df)} itens.")
        
        img_links_df = load_image_links(args.img_excel)
        logger.info(f"Planilha de links de imagens carregada com {len(img_links_df)} registros.")
        
        df = df.merge(img_links_df, how="left", left_on=c_sku, right_on="SKU")
        logger.debug("Mesclagem concluída entre produtos e links de imagem.")
        
        if c_img:
            df["FinalImageURL"] = df[c_img].fillna(df["ImageURL"])
        else:
            df["FinalImageURL"] = df["ImageURL"]

        # 2. Garantir colunas de agrupamento
        if 'Grupo' not in df.columns:
            df['Grupo'] = 'Não Classificado'
        else:
            df['Grupo'] = df['Grupo'].replace({None: '', 'None': ''}).fillna('Não Classificado')

        if 'Familia' not in df.columns:
            df['Familia'] = 'Não Classificada'
        else:
            df['Familia'] = df['Familia'].replace({None: '', 'None': ''}).fillna('Não Classificada')

        # 3. Limitar produtos se necessário
        if args.max_products > 0:
            df = df.head(args.max_products)
            logger.info(f"Limitado a {args.max_products} produtos")
        
        # 4. Processar imagens
        products = []
        for _, row in df.iterrows():
            product_dict = row.to_dict()
            product_dict['SKU'] = str(product_dict[c_sku]).strip()
            image_path = find_image_for_sku(product_dict['SKU'], args.imagens)
            final_image_url = str(product_dict.get('FinalImageURL', '')).strip()
            
            if not image_path and final_image_url and final_image_url != 'nan' and not args.skip_download:
                image_path = download_image(final_image_url, product_dict['SKU'], args.imagens)
            
            if image_path:
                base_name, ext = os.path.splitext(os.path.basename(image_path))
                optimized_path = os.path.join(args.imagens, f"optimized_{base_name}.jpg")
                optimize_image(image_path, optimized_path)
                if os.path.exists(optimized_path):
                    auto_crop_image(optimized_path)
                    product_dict['image_path'] = optimized_path
                else:
                    product_dict['image_path'] = None
            else:
                product_dict['image_path'] = None
            
            if product_dict['image_path'] or args.include_no_image:
                products.append(product_dict)
        
        # 5. Ordenar e gerar PDF
        products.sort(key=lambda x: (x.get('Grupo', ''), x.get('Familia', ''), x.get(c_nome, ''), x.get(c_sku, '')))
        create_catalog_pdf(products, args.out)
        
    except Exception as e:
        logger.error(f"Erro fatal ao gerar catálogo: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
