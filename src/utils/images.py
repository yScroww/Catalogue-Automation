import os
import requests
from PIL import Image
from io import BytesIO
from .logger import get_logger
from typing import Optional, Tuple

logger = get_logger(__name__)

# Defina a largura máxima para as imagens do catálogo
MAX_WIDTH = 800

def find_image_for_sku(sku: str, img_dir: str) -> Optional[str]:
    """
    Encontra um arquivo de imagem para o SKU fornecido no diretório de imagens.
    Retorna o caminho absoluto do arquivo se encontrado e válido, senão None.
    """
    if not os.path.isdir(img_dir):
        logger.warning(f"Diretório de imagens '{img_dir}' não encontrado. Criando...")
        os.makedirs(img_dir, exist_ok=True)
        return None
    
    for file_name in os.listdir(img_dir):
        if file_name.startswith(str(sku) + '.'):
            path = os.path.abspath(os.path.join(img_dir, file_name))
            if validate_image(path):
                return path
            else:
                logger.warning(f"Arquivo de imagem para SKU {sku} existe, mas está vazio ou inválido. Será removido.")
                os.remove(path)
    
    return None

def download_image(url: str, sku: str, img_dir: str) -> Optional[str]:
    """
    Baixa, processa e redimensiona uma imagem de uma URL, salvando-a localmente.
    """
    if not url:
        return None
    
    os.makedirs(img_dir, exist_ok=True)
    file_path = os.path.join(img_dir, f"{sku}.jpg")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))

        # Redimensiona a imagem se ela for maior que a largura máxima
        if img.width > MAX_WIDTH:
            height = int(img.height * (MAX_WIDTH / img.width))
            img = img.resize((MAX_WIDTH, height), Image.LANCZOS)
            logger.info(f"Imagem do SKU {sku} redimensionada para {MAX_WIDTH}x{height} pixels.")
        
        # Converte para RGB para garantir compatibilidade e salva
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        img.save(file_path, 'JPEG', quality=95)
        
        # Checa se o arquivo salvo tem tamanho maior que 0
        if os.path.getsize(file_path) > 0:
            logger.info(f"Imagem processada e salva com sucesso: {file_path}")
            return file_path
        else:
            logger.error(f"Imagem baixada para o SKU {sku} está vazia (0 bytes). Removendo.")
            os.remove(file_path)
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de rede/HTTP ao baixar imagem para SKU {sku} da URL {url}: {e}")
    except (IOError, SyntaxError) as e:
        logger.error(f"O conteúdo da URL para SKU {sku} não é uma imagem válida: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Arquivo de imagem inválido removido: {file_path}")
    except Exception as e:
        logger.error(f"Erro inesperado ao baixar ou salvar imagem para SKU {sku}: {e}")

    return None

def validate_image(image_path: str) -> bool:
    """Valida se o caminho da imagem existe e se o arquivo é um formato de imagem válido."""
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        return False
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except (IOError, SyntaxError):
        logger.warning(f"Arquivo '{image_path}' não é uma imagem válida.")
        return False

def get_image_dimensions(image_path: str) -> Optional[Tuple[int, int]]:
    """Obtém as dimensões de uma imagem em pixels."""
    if not validate_image(image_path):
        return None
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Erro ao obter dimensões da imagem '{image_path}': {e}")
        return None
    
    from PIL import Image

def optimize_image(input_path: str, output_path: str, max_size=(800, 800), quality=85):
    """
    Otimiza a imagem redimensionando-a e comprimindo-a.
    
    Args:
        input_path (str): Caminho para a imagem original.
        output_path (str): Caminho onde a imagem otimizada será salva.
        max_size (tuple): Tamanho máximo (largura, altura) da imagem.
        quality (int): Qualidade de compressão JPEG (0-100).
    """
    try:
        with Image.open(input_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_path, "JPEG", quality=quality, optimize=True)
            logger.info(f"Imagem otimizada de '{input_path}' para '{output_path}'.")
    except Exception as e:
        logger.error(f"Erro ao otimizar a imagem em '{input_path}': {e}")
        return False
    return True