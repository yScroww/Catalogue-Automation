import pandas as pd
from typing import Tuple, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

def pick_column(colmap: dict, *opts: str) -> Optional[str]:
    """Tenta encontrar uma coluna entre várias opções possíveis."""
    for o in opts:
        if o.lower() in colmap:
            return colmap[o.lower()]
    return None

def load_product_data(path: str) -> Tuple[pd.DataFrame, str, str, str, Optional[str]]:
    """Carrega e valida dados de produtos de uma planilha Excel."""
    try:
        df = pd.read_excel(path)
        logger.info(f"Planilha carregada: {path} com {len(df)} registros")
        
        colmap = {c.lower(): c for c in df.columns}
        
        # Tenta encontrar colunas importantes
        c_sku = pick_column(colmap, "sku", "codigo", "Código SKU", "ID")
        c_nome = pick_column(colmap, "nome", "Produto", "Nome do Produto", "Descrição")
        c_cat = pick_column(colmap, "categoria", "Categoria Primária", "Departamento", "Grupo")
        c_img = pick_column(colmap, "ImagemArquivo", "Imagem", "ImagemPath", "ImagemFile", "LinkImagem", "ImageURL")
        c_ativo = pick_column(colmap, "Ativo", "Status", "Disponível", "Ativo?")

        # Valida colunas obrigatórias
        if not all([c_sku, c_nome, c_cat]):
            raise ValueError("A planilha precisa ter colunas para SKU, Nome e Categoria")
        
        # Filtra por status ativo se a coluna existir
        if c_ativo:
            active_values = ["true", "1", "sim", "ativo", "yes", "y", "verdadeiro"]
            df = df[
                (df[c_ativo].astype(str).str.lower().isin(active_values)) |
                (df[c_ativo] == True)
            ]
            logger.info(f"Filtrado para {len(df)} produtos ativos")
        
        # Remove registros com valores nulos nas colunas críticas
        df = df.dropna(subset=[c_sku, c_nome, c_cat])
        logger.info(f"{len(df)} produtos após remover valores nulos")
        
        return df, c_sku, c_nome, c_cat, c_img
    except Exception as e:
        logger.error(f"Erro ao carregar dados de produtos: {str(e)}")
        raise

def load_image_links(path: str) -> pd.DataFrame:
    """Carrega links de imagens de uma planilha Excel."""
    try:
        df = pd.read_excel(path)
        logger.info(f"Planilha de imagens carregada: {path} com {len(df)} registros")
        
        colmap = {c.lower(): c for c in df.columns}
        c_sku = pick_column(colmap, "sku", "código", "id produto", "product id")
        c_url = None
        
        # Procura por coluna que parece ser URL
        for c in colmap:
            if "http" in c or "url" in c or "link" in c or "imagem" in c:
                c_url = colmap[c]
                break
        
        if not c_sku or not c_url:
            raise ValueError("A planilha de imagens precisa ter colunas para SKU e URL")
        
        # Filtra e renomeia colunas
        df = df.dropna(subset=[c_sku, c_url])
        df = df[[c_sku, c_url]].rename(columns={c_sku: "SKU", c_url: "ImageURL"})
        
        logger.info(f"{len(df)} links de imagem válidos encontrados")
        return df
    
    except Exception as e:
        logger.error(f"Erro ao carregar links de imagem: {str(e)}")
        raise