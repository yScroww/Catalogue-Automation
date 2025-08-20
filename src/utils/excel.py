import os
import pandas as pd
from .logger import get_logger
from typing import Tuple, List, Optional

logger = get_logger(__name__)

def find_columns(df: pd.DataFrame, names: List[str]) -> Tuple[str, ...]:
    """Tenta encontrar as colunas no DataFrame, lidando com maiúsculas/minúsculas e espaços."""
    cols = []
    df_cols = [c.strip().lower() for c in df.columns]
    for name in names:
        try:
            # Encontra a coluna com base no nome
            col_name = df.columns[df_cols.index(name.lower())]
            cols.append(col_name)
        except ValueError:
            raise ValueError(f"A coluna obrigatória '{name}' não foi encontrada na planilha.")
    return tuple(cols) 

def load_product_data(file_path: str) -> Tuple[pd.DataFrame, str, str, str, Optional[str]]:
    """
    Carrega os dados da planilha de produtos e retorna o DataFrame e os nomes das colunas.
    """
    logger.info(f"Carregando planilha: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    # Tenta carregar a planilha 'Catálogo de Produtos' primeiro
    try:
        df = pd.read_excel(file_path, sheet_name='Catálogo de Produtos')
    except ValueError:
        # Se a planilha não for encontrada, carrega a primeira planilha
        df = pd.read_excel(file_path)

    # Verifica e trata as colunas obrigatórias
    try:
        c_sku, c_nome, c_cat = find_columns(df, ['SKU', 'Nome do Produto', 'Grupo'])
    except ValueError as e:
        raise ValueError(f"Planilha de produtos inválida: {e}")

    # A coluna de imagem é opcional na planilha de produtos
    c_img = None
    try:
        c_img = find_columns(df, ['Imagem'])[0]
    except ValueError:
        logger.info("Coluna 'Imagem' não encontrada na planilha de produtos, usando apenas a base de links de imagem.")

    # Remove linhas onde as colunas essenciais estão nulas
    df = df.dropna(subset=[c_sku, c_nome, c_cat])
    logger.info(f"{len(df)} produtos após remover valores nulos")

    return df, c_sku, c_nome, c_cat, c_img


def load_image_links(file_path: str) -> pd.DataFrame:
    """
    Carrega a planilha de links de imagens.
    """
    logger.info(f"Carregando planilha de imagens: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    df = pd.read_excel(file_path)

    try:
        c_sku, c_image_url = find_columns(df, ['SKU', 'Imagem Principal'])
        df = df[[c_sku, c_image_url]].copy()
        df.rename(columns={c_sku: 'SKU', c_image_url: 'ImageURL'}, inplace=True)
    except ValueError as e:
        raise ValueError(f"Planilha de imagens deve conter as colunas 'SKU' e 'Imagem Principal'. Erro: {e}")

    # Drop duplicates based on SKU
    dupes = df['SKU'].duplicated(keep='first').sum()
    if dupes > 0:
        logger.warning(f"Foram encontradas e removidas {dupes} SKUs duplicadas na base de imagens.")
    df.drop_duplicates(subset=['SKU'], keep='first', inplace=True)
    
    # Filter out rows with no image link
    df = df.dropna(subset=['ImageURL'])
    logger.info(f"{len(df)} links de imagem e fornecedor válidos encontrados")
    return df