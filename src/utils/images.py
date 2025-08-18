import os
import requests
from PIL import Image
from io import BytesIO
from .logger import get_logger

logger = get_logger(__name__)

def find_image_for_sku(sku, img_dir="data/images"):
    """
    Encontra um arquivo de imagem para o SKU fornecido no diretório de imagens.
    Retorna o caminho absoluto do arquivo se encontrado e válido, senão None.
    """
    if not os.path.isdir(img_dir):
        logger.warning(f"Diretório de imagens '{img_dir}' não encontrado. Criando...")
        os.makedirs(img_dir, exist_ok=True)
        return None
        
    for file_name in os.listdir(img_dir):
        # A busca agora é mais flexível para corresponder a arquivos com diferentes extensões
        if file_name.startswith(str(sku) + '.'):
            path = os.path.abspath(os.path.join(img_dir, file_name))
            # Simplesmente verifica se o arquivo existe e tem tamanho > 0
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return path
            else:
                logger.warning(f"Arquivo de imagem para SKU {sku} existe, mas está vazio ou inválido. Será ignorado.")
    
    return None

def download_image(url, sku, img_dir="data/images"):
    """Baixa uma imagem de uma URL, limpa e a salva localmente em formato JPEG."""
    file_path = None
    try:
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Define o caminho do arquivo para salvar como JPEG, que é mais compatível
        file_path = os.path.join(img_dir, f"{sku}.jpg")
        
        # Tenta abrir o conteúdo binário com PIL
        with Image.open(BytesIO(response.content)) as img:
            # Converte a imagem para um modo de cor compatível (RGB) e a salva
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(file_path, 'JPEG')
            logger.info(f"Imagem processada e salva em um formato limpo: {file_path}")
        
        # Checa se o arquivo salvo tem tamanho maior que 0
        if os.path.getsize(file_path) > 0:
            logger.info(f"Imagem para SKU {sku} salva com sucesso.")
            return True
        else:
            logger.error(f"Imagem baixada para o SKU {sku} está vazia (0 bytes). Removendo.")
            os.remove(file_path)
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de rede/HTTP ao baixar imagem para SKU {sku} da URL {url}: {e}")
        return False
    except (IOError, SyntaxError) as e:
        logger.error(f"O conteúdo da URL para SKU {sku} não é uma imagem válida: {e}")
        if file_path and os.path.exists(file_path):
            os.remove(file_path) # Remove o arquivo inválido
            logger.info(f"Arquivo de imagem inválido removido: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao baixar ou salvar imagem para SKU {sku}: {e}")
        return False