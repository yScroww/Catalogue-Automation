import argparse
import pandas as pd
import os
import sys
from src.pdf_builder import create_catalog_pdf
from src.utils.logger import get_logger
from src.utils.excel import load_product_data, load_image_links
from src.utils.images import find_image_for_sku, download_image, optimize_image, auto_crop_image

logger = get_logger(__name__)

# -------------------------------
# Parsing de argumentos
# -------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Gerador de Catálogo em PDF",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--excel", default="data/produtos.xlsx")
    parser.add_argument("--img-excel", default="data/base_imagens.xlsx")
    parser.add_argument("--imagens", default="data/imagens")
    parser.add_argument("--template", default=None)
    parser.add_argument("--out", type=str, default="Catalogo_Nordesa.pdf")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--include-no-image", action="store_true")
    parser.add_argument("--max-products", type=int, default=0)
    return parser.parse_args()

# -------------------------------
# Funções auxiliares
# -------------------------------
def prepare_dataframe(excel_path, img_excel_path):
    """Carrega planilhas, mescla dados e garante colunas obrigatórias."""
    df, c_sku, c_nome, c_cat, c_img = load_product_data(excel_path)
    logger.info(f"Planilha de produtos carregada com {len(df)} itens.")

    # Aplicar o filtro de produtos com estoque > 0
    if 'Estoque' in df.columns:
        df = df[df['Estoque'] > 0]
        logger.info(f"Filtro aplicado. Restam {len(df)} produtos com estoque > 0.")
    else:
        logger.warning("Coluna 'Estoque' não encontrada. Ignorando filtro de estoque.")

    # NOVO FILTRO: Adicionar a condição para a coluna 'Promocional'
    if 'Promocional' in df.columns:
        df = df[df['Promocional'].str.upper().str.strip() == 'NAO']
        logger.info(f"Filtro promocional aplicado. Restam {len(df)} produtos não promocionais.")
    else:
        logger.warning("Coluna 'Promocional' não encontrada. Ignorando filtro promocional.")

    # Normalizar a coluna 'Nome Força' para evitar erros de case/espaços e renomear
    if 'Nome Força' in df.columns:
        df['Nome Força'] = df['Nome Força'].str.strip()
        df['Nome Força'] = df['Nome Força'].str.title()
        df = df.rename(columns={'Nome Força': 'Nome da Força'})

    img_links_df = load_image_links(img_excel_path)
    logger.info(f"Planilha de links de imagens carregada com {len(img_links_df)} registros.")

    df = df.merge(img_links_df, how="left", left_on=c_sku, right_on="SKU")
    logger.debug("Mesclagem concluída entre produtos e links de imagem.")

    # Definir coluna de imagem final
    df["FinalImageURL"] = df[c_img].fillna(df["ImageURL"]) if c_img else df["ImageURL"]

    # Garantir colunas de agrupamento
    for col, default in [("Grupo", "Não Classificado"), ("Familia", "Não Classificado")]:
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].replace({None: '', 'None': ''}).fillna(default)

    return df, c_sku, c_nome

def process_image_for_sku(sku, final_url, img_dir, skip_download=False):
    """
    Garanta que uma imagem otimizada esteja disponível para o SKU.
    Retorna caminho da imagem pronta ou None.
    """
    # Verificar imagem já existente
    image_path = find_image_for_sku(sku, img_dir)

    # Se não existe, baixar (se permitido)
    if not image_path and final_url and final_url.lower() != 'nan' and not skip_download:
        image_path = download_image(final_url, sku, img_dir)

    if not image_path:
        return None

    base_name, _ = os.path.splitext(os.path.basename(image_path))
    optimized_path = os.path.join(img_dir, f"optimized_{base_name}.jpg")

    # Evitar retrabalho se já otimizada
    if os.path.exists(optimized_path) and os.path.getsize(optimized_path) > 0:
        logger.debug(f"Imagem já otimizada para SKU {sku}: {optimized_path}")
        return optimized_path

    # Otimizar e cortar
    if optimize_image(image_path, optimized_path):
        auto_crop_image(optimized_path)
        return optimized_path
    else:
        logger.warning(f"Falha ao otimizar imagem para SKU {sku}")
        return None

def build_products_list(df, c_sku, c_nome, imagens_dir, include_no_image=False, skip_download=False):
    """Cria lista final de produtos com imagens prontas."""
    products = []
    
    for _, row in df.iterrows():
        product_dict = row.to_dict()
        product_dict['SKU'] = str(product_dict[c_sku]).strip()
        final_url = str(product_dict.get('FinalImageURL', '')).strip()

        # Usa o caminho da pasta de imagens fornecido
        image_path = process_image_for_sku(
            product_dict['SKU'], final_url, imagens_dir, skip_download=skip_download
        )
        product_dict['image_path'] = image_path

        # O filtro de imagem agora é condicional
        if not include_no_image and not image_path:
            continue
        
        products.append(product_dict)

    # Ordenar para consistência
    products.sort(key=lambda x: (x.get('Grupo', ''), x.get('Familia', ''), x.get(c_nome, ''), x.get(c_sku, '')))
    return products

# -------------------------------
# Função principal
# -------------------------------

def main(excel_path, img_excel_path, imagens_path, capas_path):
    try:
        args = parse_args()
        
        # 1. Preparar dados
        df, c_sku, c_nome = prepare_dataframe(excel_path, img_excel_path)
        if args.max_products > 0:
            df = df.head(args.max_products)
            logger.info(f"Limitado a {args.max_products} produtos")

        # 2. Obter a lista completa de produtos com estoque > 0 e não promocionais
        all_products_with_stock = build_products_list(
            df.copy(), c_sku, c_nome, imagens_path,
            include_no_image=True, skip_download=args.skip_download
        )

        # 3. Preparar imagens e a lista final de produtos com filtro de imagens
        products = build_products_list(
            df, c_sku, c_nome, imagens_path,
            include_no_image=args.include_no_image, skip_download=args.skip_download
        )
        logger.info(f"{len(products)} produtos prontos para geração do catálogo.")

        # 4. Unir listas e criar o arquivo de status
        sku_with_image = {p['SKU'] for p in products}

        # O caminho de saída para o PDF e o CSV é o mesmo
        output_dir = r"\\192.168.0.7\Depto Comercial\04-Habilidades para vencer\05-Catálago"
        
        # Criar a lista de status
        status_products = []
        for p in all_products_with_stock:
            p['Adicionado ao Catalogo'] = 'Sim' if p['SKU'] in sku_with_image else 'Nao'
            status_products.append(p)

        if status_products:
            df_status = pd.DataFrame(status_products)
            # Salvar o CSV no diretório de rede
            output_path_csv = os.path.join(output_dir, "status_catalogo.csv")
            df_status[['SKU', 'Nome do Produto', 'Adicionado ao Catalogo']].to_csv(output_path_csv, index=False)
            logger.info(f"Tabela de status do catálogo gerada em '{output_path_csv}'.")

        # 5. Adicionar verificação de lista de produtos para evitar PDF de apenas uma capa
        if not products:
            logger.warning("Nenhum produto com estoque maior que zero, não promocional e com imagem encontrada. O catálogo não será gerado.")
            return

        # 6. Gerar PDF
        output_path_pdf = os.path.join(output_dir, args.out)
        create_catalog_pdf(products, output_path_pdf, capas_path) # Alterado aqui

        logger.info("Geração do catálogo concluída.")

    except Exception as e:
        logger.error(f"Erro fatal ao gerar catálogo: {str(e)}", exc_info=True)
        raise
