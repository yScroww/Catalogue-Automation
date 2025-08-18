import os
import requests
from typing import Tuple, Optional
from PIL import Image
from utils.logger import get_logger

logger = get_logger(__name__)

def find_image_for_sku(sku: str, imagens_dir: str, explicit_path: str = "") -> Optional[str]:
    """Busca imagem local para um SKU, testando vários formatos."""
    if explicit_path and os.path.isfile(explicit_path):
        if validate_image(explicit_path):
            return explicit_path
        return None
    
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        path = os.path.join(imagens_dir, f"{sku}{ext}")
        if os.path.isfile(path) and validate_image(path):
            return path
    return None

def download_image(url: str, sku: str, imagens_dir: str) -> Optional[str]:
    """Baixa imagem de uma URL e salva localmente."""
    if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        logger.warning(f"URL inválida para SKU {sku}: {url}")
        return None
    
    os.makedirs(imagens_dir, exist_ok=True)
    local_path = os.path.join(imagens_dir, f"{sku}.jpg")
    
    try:
        response = requests.get(url, timeout=15, stream=True)
        response.raise_for_status()
        
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        if validate_image(local_path):
            logger.debug(f"Imagem salva: {local_path}")
            return local_path
        else:
            os.remove(local_path)
            logger.error(f"Imagem baixada é inválida: {local_path}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao baixar imagem para SKU {sku}: {str(e)}")
        if os.path.exists(local_path):
            os.remove(local_path)
        return None

def validate_image(image_path: str) -> bool:
    """Verifica se a imagem é válida."""
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except (IOError, SyntaxError) as e:
        logger.error(f"Imagem inválida: {image_path} - {str(e)}")
        return False

def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """Obtém dimensões da imagem."""
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Erro ao ler dimensões: {image_path} - {str(e)}")
        return (0, 0)