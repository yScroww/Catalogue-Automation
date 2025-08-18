import pandas as pd
import requests
from io import BytesIO
from .logger import get_logger
import os

logger = get_logger(__name__)

# Mapeia os nomes das colunas da planilha para as variáveis do script
COL_MAP = {
    "sku": ["SKU", "Sku", "sku"],
    "nome_produto": ["Nome do Produto", "NomeProduto", "Nome", "Produto"],
    "grupo": ["Grupo", "Família", "Categoria"],
    "marca": ["Marca", "marca", "Brand", "Fornecedor"]
}

def load_product_data(file_path):
    """Carrega a planilha de produtos e padroniza as colunas."""
    logger.info(f"Carregando planilha: {file_path}")
    
    file_extension = os.path.splitext(file_path)[1].lower()
    df = None
    
    # Tenta carregar a planilha com o nome 'Catálogo de Produtos' primeiro
    try:
        if file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, sheet_name='Catálogo de Produtos')
        elif file_extension == '.csv':
            df = pd.read_csv(file_path)
    except ValueError:
        logger.warning("Planilha 'Catálogo de Produtos' não encontrada. Tentando carregar a primeira planilha.")
        try:
            if file_extension in ['.xlsx', '.xls']:
                # Tenta carregar a primeira planilha se a nomeada não for encontrada
                df = pd.read_excel(file_path)
            elif file_extension == '.csv':
                df = pd.read_csv(file_path)
        except FileNotFoundError:
            logger.error(f"Arquivo não encontrado: {file_path}")
            raise
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {file_path}")
        raise
    
    if df is None:
        logger.error(f"Formato de arquivo não suportado ou erro de leitura: {file_path}")
        raise ValueError("Formato de arquivo não suportado ou erro de leitura.")

    # Encontra os nomes reais das colunas essenciais
    c_sku = next((col for col in df.columns if col in COL_MAP["sku"]), None)
    c_nome = next((col for col in df.columns if col in COL_MAP["nome_produto"]), None)
    c_cat = next((col for col in df.columns if col in COL_MAP["grupo"]), None)
    
    # A coluna de marca é opcional nesta planilha
    c_marca = next((col for col in df.columns if col in COL_MAP["marca"]), None)
    
    missing_cols = []
    if not c_sku:
        missing_cols.append("SKU")
    if not c_nome:
        missing_cols.append("Nome do Produto")
    if not c_cat:
        missing_cols.append("Grupo/Família")
    
    if missing_cols:
        logger.error(f"Colunas essenciais ({', '.join(missing_cols)}) não encontradas na planilha.")
        raise ValueError("Planilha com formato inválido. Verifique os nomes das colunas.")

    # Remove linhas onde as colunas essenciais estão vazias
    df = df.dropna(subset=[c_sku, c_nome, c_cat]).reset_index(drop=True)
    logger.info(f"{len(df)} produtos após remover valores nulos")
    
    return df, c_sku, c_nome, c_cat, c_marca

def load_image_links(file_path):
    """Carrega a planilha com links de imagem, remove duplicatas e padroniza a coluna 'ImageURL'."""
    logger.info(f"Carregando planilha de imagens: {file_path}")
    
    file_extension = os.path.splitext(file_path)[1].lower()
    df = None
    
    try:
        if file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_extension == '.csv':
            df = pd.read_csv(file_path)
        else:
            logger.error(f"Formato de arquivo não suportado: {file_path}")
            raise ValueError("Formato de arquivo não suportado.")
    except FileNotFoundError:
        logger.error(f"Arquivo de links de imagem não encontrado: {file_path}")
        raise
    
    # Mapeia as colunas do seu arquivo de imagens
    if "SKU" not in df.columns or "Imagem Principal" not in df.columns or "Fornecedor" not in df.columns:
        logger.error("As colunas 'SKU', 'Imagem Principal' e 'Fornecedor' não foram encontradas na planilha de imagens.")
        raise ValueError("Planilha de links de imagem com formato inválido.")
    
    # Remove linhas com valores nulos nas colunas essenciais
    df = df.dropna(subset=["SKU", "Imagem Principal", "Fornecedor"]).reset_index(drop=True)
    
    # --- NOVO TRECHO DE CÓDIGO ---
    # Remove SKUs duplicados, mantendo a primeira ocorrência
    df_count_before = len(df)
    df = df.drop_duplicates(subset=["SKU"], keep='first').reset_index(drop=True)
    if len(df) < df_count_before:
        logger.warning(f"Foram encontradas e removidas {df_count_before - len(df)} SKUs duplicadas na base de imagens.")
    # --- FIM DO NOVO TRECHO ---

    # Renomeia as colunas antes do merge para evitar qualquer conflito
    df = df.rename(columns={"SKU": "SKU_img", "Imagem Principal": "ImageURL", "Fornecedor": "Marca_img"})
    
    logger.info(f"{len(df)} links de imagem e fornecedor válidos encontrados")
    return df