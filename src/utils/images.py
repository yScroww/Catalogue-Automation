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

# -------------------------
# Localização / Download
# -------------------------

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
                try:
                    os.remove(path)
                except Exception:
                    pass
    
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
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content)).convert('RGB')

        # Redimensiona se for muito grande
        if img.width > MAX_WIDTH:
            height = int(img.height * (MAX_WIDTH / img.width))
            img = img.resize((MAX_WIDTH, height), Image.Resampling.LANCZOS)
            logger.info(f"Imagem do SKU {sku} redimensionada para {MAX_WIDTH}x{height} pixels.")
        
        img.save(file_path, 'JPEG', quality=80)
        
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
            try:
                os.remove(file_path)
                logger.info(f"Arquivo de imagem inválido removido: {file_path}")
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Erro inesperado ao baixar ou salvar imagem para SKU {sku}: {e}")

    return None

# -------------------------
# Validação / Utilitários
# -------------------------

def validate_image(image_path: str) -> bool:
    """Valida se o caminho da imagem existe e se o arquivo é um formato de imagem válido."""
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        return False
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
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


def optimize_image(input_path: str, output_path: str, max_size=(800, 800), quality=80) -> bool:
    """
    Otimiza a imagem redimensionando-a e comprimindo-a.
    Mantém proporção e nunca amplia.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert('RGB')
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_path, "JPEG", quality=quality, optimize=True)
            logger.info(f"Imagem otimizada de '{input_path}' para '{output_path}'.")
    except Exception as e:
        logger.error(f"Erro ao otimizar a imagem em '{input_path}': {e}")
        return False
    return True

# -------------------------
# Corte Inteligente
# -------------------------

def _to_numpy_rgb(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert('RGB'))  # H x W x 3


def _row_stats(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Retorna:
      - nonwhite_ratio_por_linha: fração de pixels não-fundo (≠ branco dentro de tolerância)
      - row_std: soma do desvio padrão por canal (medida de uniformidade da linha)
    """
    h, w, _ = rgb.shape
    # Distância de cada pixel para o branco puro
    diff = 255 - rgb  # maior = mais escuro/mais colorido que branco
    # norma L1 por pixel
    l1 = diff.astype(np.int16)
    l1 = np.abs(l1).sum(axis=2)  # H x W (0 para branco puro)
    return l1, w


def _compute_nonwhite_and_std(rgb: np.ndarray, bg_tolerance: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcula métricas por linha:
      - nonwhite_ratio: fração de pixels cuja distância L1 ao branco > 3*bg_tolerance
      - row_std_sum: soma dos desvios padrão dos 3 canais (uniformidade da linha)
    """
    h, w, _ = rgb.shape
    arr = rgb.astype(np.int16)
    # Distância L1 ao branco (255,255,255)
    l1 = np.abs(255 - arr).sum(axis=2)  # H x W
    # Pixel "não fundo" se l1 > 3*bg_tolerance
    mask_nonwhite = l1 > (3 * bg_tolerance)
    nonwhite_ratio = mask_nonwhite.mean(axis=1)  # por linha

    # desvio padrão por canal, somado (menor => linha mais uniforme/sólida)
    std_r = arr[:,:,0].std(axis=1)
    std_g = arr[:,:,1].std(axis=1)
    std_b = arr[:,:,2].std(axis=1)
    row_std_sum = std_r + std_g + std_b

    return nonwhite_ratio, row_std_sum


def _bbox_from_mask(mask: np.ndarray, padding: int, width: int, height: int) -> Optional[Tuple[int,int,int,int]]:
    """
    BBox do conteúdo (True = conteúdo). Retorna (left, upper, right, lower) já com padding.
    """
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return None
    left = max(0, xs.min() - padding)
    right = min(width, xs.max() + 1 + padding)
    upper = max(0, ys.min() - padding)
    lower = min(height, ys.max() + 1 + padding)
    return (left, upper, right, lower)


def _paste_on_square(img: Image.Image, size: int = 800, bg=(255, 255, 255)) -> Image.Image:
    """
    Coloca a imagem (preservando proporção) sobre um canvas quadrado branco.
    Garante saídas 1:1 alinhadas e consistentes para o PDF.
    """
    img = img.convert('RGB')
    w, h = img.size
    scale = min(size / w, size / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new('RGB', (size, size), bg)
    off_x = (size - new_w) // 2
    off_y = (size - new_h) // 2
    canvas.paste(img_resized, (off_x, off_y))
    return canvas


def auto_crop_image(image_path: str,
    padding=12, bg_tolerance=20, text_row_density=0.10,
    uniform_row_std=5.0, max_subtitle_fraction=0.30,
    final_square_size=800) -> bool:
    try:
        with Image.open(image_path) as im:
            im = im.convert('RGB')
            arr = np.asarray(im)
            h,w,_ = arr.shape

            # Métricas por linha
            diff = np.abs(255-arr).sum(axis=2)
            mask = diff>(3*bg_tolerance)
            nonwhite = mask.mean(axis=1)
            std_rows = arr.std(axis=2).mean(axis=1)

            # Gradiente vertical
            grad = np.abs(np.diff(nonwhite,n=1,prepend=0))

            max_cut = int(h*max_subtitle_fraction)
            cut=0
            for i in range(h-1,max(h-1-max_cut,-1),-1):
                if (nonwhite[i]<text_row_density or std_rows[i]<uniform_row_std) and grad[i]>0.02:
                    cut+=1
                else:
                    break

            if cut>15: # só corta se for significativo
                im=im.crop((0,0,w,h-cut))
                arr=np.asarray(im)
                h,w,_=arr.shape
                mask = np.abs(255-arr).sum(axis=2)>(3*bg_tolerance)

            # Bounding box lateral
            ys,xs=np.where(mask)
            if len(xs)>0:
                left=max(0,xs.min()-padding)
                right=min(w,xs.max()+1+padding)
                upper=max(0,ys.min()-padding)
                lower=min(h,ys.max()+1+padding)
                im=im.crop((left,upper,right,lower))

            # Canvas quadrado
            im.thumbnail((final_square_size,final_square_size),Image.Resampling.LANCZOS)
            canvas=Image.new('RGB',(final_square_size,final_square_size),(255,255,255))
            offx=(final_square_size-im.width)//2
            offy=(final_square_size-im.height)//2
            canvas.paste(im,(offx,offy))
            canvas.save(image_path,"JPEG",quality=80,optimize=True)
        return True
    except Exception as e:
        logger.error(f"Erro ao cortar {image_path}: {e}")
        return False