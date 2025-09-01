# src/utils/images.py
import os
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple

from .logger import get_logger

logger = get_logger(__name__)
MAX_WIDTH = 800
JPEG_QUALITY = 80

# ============================================================
# Localização / Download
# ============================================================

def find_image_for_sku(sku: str, img_dir: str) -> Optional[str]:
    """
    Procura uma imagem já salva para o SKU no diretório especificado.
    Retorna o caminho absoluto se for válida, senão None.
    """
    logger.info(f"Procurando imagens para o SKU {sku} no diretório: {img_dir}")

    if not os.path.isdir(img_dir):
        os.makedirs(img_dir, exist_ok=True)
        return None

    for file_name in os.listdir(img_dir):
        if file_name.startswith(str(sku) + '.'):
            path = os.path.abspath(os.path.join(img_dir, file_name))
            if validate_image(path):
                logger.debug(f"Imagem já existente para SKU {sku}: {path}")
                return path
            else:
                logger.warning(f"Imagem existente para SKU {sku} é inválida. Será removida.")
                try:
                    os.remove(path)
                except Exception:
                    pass
    return None


def download_image(url: str, sku: str, img_dir: str) -> Optional[str]:
    """
    Baixa e salva a imagem original de uma URL para o SKU.
    """
    if not url:
        return None

    os.makedirs(img_dir, exist_ok=True)
    file_path = os.path.join(img_dir, f"{sku}.jpg")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert('RGB')

        # Redimensiona se for muito grande
        if img.width > MAX_WIDTH:
            height = int(img.height * (MAX_WIDTH / img.width))
            img = img.resize((MAX_WIDTH, height), Image.Resampling.LANCZOS)
            logger.info(f"Imagem SKU {sku} redimensionada para {MAX_WIDTH}x{height}px")

        img.save(file_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
        if os.path.getsize(file_path) > 0:
            logger.info(f"Imagem SKU {sku} salva com sucesso: {file_path} ({os.path.getsize(file_path)//1024} KB)")
            return file_path
        else:
            logger.error(f"Imagem SKU {sku} vazia (0 bytes). Removendo.")
            os.remove(file_path)
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar imagem SKU {sku} da URL {url}: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao salvar imagem SKU {sku}: {e}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    return None

# ============================================================
# Validação / Utilitários
# ============================================================

def validate_image(image_path: str) -> bool:
    """
    Verifica se a imagem existe e é válida.
    """
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        return False
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        logger.warning(f"Arquivo de imagem inválido: {image_path}")
        return False


def optimize_image(input_path: str, max_size=(800, 800), quality=80) -> bool:
    """
    Redimensiona e otimiza a imagem mantendo proporção.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert('RGB')
            orig_size = os.path.getsize(input_path)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(input_path, "JPEG", quality=quality, optimize=True)
            logger.info(
                f"Otimizada imagem '{input_path}' "
                f"({orig_size//1024} KB → {os.path.getsize(input_path)//1024} KB)"
            )
        return True
    except Exception as e:
        logger.error(f"Erro ao otimizar imagem '{input_path}': {e}")
        return False


def get_image_dimensions(image_path: str) -> Optional[Tuple[int, int]]:
    """
    Retorna dimensões da imagem em pixels.
    """
    if not validate_image(image_path):
        return None
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Erro ao obter dimensões da imagem '{image_path}': {e}")
        return None

# ============================================================
# Corte Inteligente
# ============================================================

def auto_crop_image(image_path: str,
                    padding=12, bg_tolerance=20, text_row_density=0.10,
                    uniform_row_std=5.0, max_subtitle_fraction=0.30,
                    final_square_size=800) -> bool:
    """
    Remove subtítulos/bordas brancas e centraliza a imagem em um canvas quadrado.
    """
    try:
        with Image.open(image_path) as im:
            im = im.convert('RGB')
            arr = np.asarray(im)
            h, w, _ = arr.shape

            # Métricas por linha
            diff = np.abs(255 - arr).sum(axis=2)
            mask = diff > (3 * bg_tolerance)
            nonwhite = mask.mean(axis=1)
            std_rows = arr.std(axis=2).mean(axis=1)
            grad = np.abs(np.diff(nonwhite, n=1, prepend=0))

            # Corte inferior
            max_cut = int(h * max_subtitle_fraction)
            cut = 0
            for i in range(h-1, max(h-1-max_cut, -1), -1):
                if (nonwhite[i] < text_row_density or std_rows[i] < uniform_row_std) and grad[i] > 0.02:
                    cut += 1
                else:
                    break

            if cut > 15:
                im = im.crop((0, 0, w, h-cut))
                arr = np.asarray(im)
                h, w, _ = arr.shape
                mask = np.abs(255-arr).sum(axis=2) > (3*bg_tolerance)

            # Bounding box lateral
            ys, xs = np.where(mask)
            if len(xs) > 0:
                left = max(0, xs.min()-padding)
                right = min(w, xs.max()+1+padding)
                upper = max(0, ys.min()-padding)
                lower = min(h, ys.max()+1+padding)
                im = im.crop((left, upper, right, lower))

            # Canvas quadrado final
            im.thumbnail((final_square_size, final_square_size), Image.Resampling.LANCZOS)
            canvas = Image.new('RGB', (final_square_size, final_square_size), (255, 255, 255))
            offx = (final_square_size - im.width) // 2
            offy = (final_square_size - im.height) // 2
            canvas.paste(im, (offx, offy))
            canvas.save(image_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

        logger.debug(f"Corte automático aplicado com sucesso: {image_path}")
        return True
    except Exception as e:
        logger.error(f"Erro ao cortar {image_path}: {e}")
        return False

# ============================================================
# Função de alto nível para pipeline de imagens
# ============================================================

def prepare_image_for_sku(sku: str, url: str, img_dir: str) -> Optional[str]:
    """
    Verifica se a imagem do SKU já existe otimizada; 
    caso contrário, baixa, otimiza e aplica corte automático.
    """
    # 1. Verificar se já existe imagem pronta
    existing = find_image_for_sku(sku, img_dir)
    if existing and validate_image(existing):
        logger.info(f"Imagem SKU {sku} já otimizada: {existing}")
        return existing

    # 2. Baixar imagem
    downloaded = download_image(url, sku, img_dir)
    if not downloaded:
        return None

    # 3. Otimizar e cortar imagem
    if optimize_image(downloaded) and auto_crop_image(downloaded):
        logger.info(f"Imagem SKU {sku} pronta para uso.")
        return downloaded
    else:
        logger.error(f"Falha ao preparar imagem do SKU {sku}.")
        return None