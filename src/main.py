import argparse
import pandas as pd
import logging
import os
from src.pdf_builder import create_catalog_pdf
from src.utils.logger import get_logger
from src.utils.excel import load_product_data, load_image_links
from src.utils.images import find_image_for_sku, download_image, optimize_image

logger = get_logger(__name__)

def parse_args():
    """Configura e parseia argumentos de linha de comando para o gerador de catálogo PDF."""
    parser = argparse.ArgumentParser(
        description="Gerador de Catálogo em PDF",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Argumentos principais
    parser.add_argument("--excel", default="data/produtos.xlsx",
                        help="Planilha com dados dos produtos")
    parser.add_argument("--img-excel", default="data/base_imagens.xlsx",
                        help="Planilha com links das imagens")
    parser.add_argument("--imagens", default="data/imagens",
                        help="Pasta onde as imagens serão salvas")
    parser.add_argument("--template", default=None,
                        help="Argumento ignorado para PDF.")
    parser.add_argument("--out", type=str, default="catalogo_gerado.pdf",
                        help="Arquivo de saída do catálogo")
    
    # Opções de processamento
    parser.add_argument("--skip-download", action="store_true",
                        help="Pular download de imagens (usar apenas locais)")
    parser.add_argument("--include-no-image", action="store_true",
                        help="Incluir produtos sem imagem disponível")
    parser.add_argument("--max-products", type=int, default=0,
                        help="Número máximo de produtos a processar (0 para todos)")
    
    # Argumentos de layout não são mais necessários para PDF (serão ignorados)
    parser.add_argument("--layout", help=argparse.SUPPRESS)
    parser.add_argument("--cols", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--rows", type=int, help=argparse.SUPPRESS)

    return parser.parse_args()

def main():
    try:
        args = parse_args()
        
        logger.info("Iniciando geração do catálogo em PDF...")
        
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
        products = []
        for _, row in df.iterrows():
            product_dict = row.to_dict()
            product_dict['SKU'] = str(product_dict[c_sku]).strip()
            
            # Localiza a imagem
            image_path = find_image_for_sku(product_dict['SKU'], args.imagens)
            final_image_url = str(product_dict.get('FinalImageURL', '')).strip()
            
            # Se não encontrar e o download for permitido, tenta baixar
            if not image_path and final_image_url and final_image_url != 'nan' and not args.skip_download:
                image_path = download_image(final_image_url, product_dict['SKU'], args.imagens)
            
            # --- Adicionado: Otimiza a imagem antes de adicionar ao PDF ---
            if image_path:
                base_name, ext = os.path.splitext(os.path.basename(image_path))
                optimized_path = os.path.join(args.imagens, f"optimized_{base_name}.jpg")
                optimize_image(image_path, optimized_path)
                
                # Usa o caminho da imagem otimizada para o PDF
                product_dict['image_path'] = optimized_path
            else:
                # Se não houver imagem, garante que o caminho seja None
                product_dict['image_path'] = None
            # -----------------------------------------------------------------
            
            if product_dict['image_path'] or args.include_no_image:
                products.append(product_dict)
        
        # 6. Ordena e agrupa produtos
        products.sort(key=lambda x: (x.get(c_cat, ''), x.get(c_nome, ''), x.get(c_sku, '')))
        logger.info("Produtos processados e ordenados.")

        # 7. Gera o catálogo em PDF
        create_catalog_pdf(products, args.out)
        
    except Exception as e:
        logger.error(f"Erro fatal ao gerar catálogo: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()