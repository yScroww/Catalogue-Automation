import os
import requests
import numpy as np
from PIL import Image as PilImage
from PIL.Image import Image as PILImageType
from io import BytesIO
from typing import Optional, Tuple

from .logger import get_logger

logger = get_logger(__name__)

# -------------------------
# Configurações globais
# -------------------------
FINAL_SIZE = 600              # pixels (quadrado final para todas as imagens)
JPEG_QUALITY = 70             # qualidade JPEG (0-100)
MAX_DOWNLOAD_WIDTH = 1200     # largura máxima ao baixar imagens originais
CROP_PADDING = 12             # padding ao cortar bordas
BG_TOLERANCE = 20             # tolerância para identificar fundo branco
TEXT_ROW_DENSITY = 0.10       # densidade máxima para linha de texto
UNIFORM_ROW_STD = 5.0         # limite para identificar faixa sólida
MAX_SUBTITLE_FRACTION = 0.30  # fração máxima para corte inferior

# -------------------------
# Localização / Download
# -------------------------
def find_image_for_sku(sku: str, img_dir: str, prefer_optimized: bool = True) -> Optional[str]:
    """Procura imagem de SKU. Se prefer_optimized=True, prioriza 'optimized_{sku}.jpg'."""
    if not os.path.isdir(img_dir):
        os.makedirs(img_dir, exist_ok=True)
        return None

    optimized_path = os.path.abspath(os.path.join(img_dir, f"optimized_{sku}.jpg"))
    if prefer_optimized and os.path.exists(optimized_path) and validate_image(optimized_path):
        logger.debug(f"[REUSE] Imagem otimizada encontrada para SKU {sku}: {optimized_path}")
        return optimized_path

    for file_name in os.listdir(img_dir):
        if file_name.startswith(str(sku) + "."):
            path = os.path.abspath(os.path.join(img_dir, file_name))
            if validate_image(path):
                logger.debug(f"[FOUND] Imagem encontrada para SKU {sku}: {path}")
                return path
            else:
                logger.warning(f"Arquivo inválido para SKU {sku}: {path} (removendo).")
                try:
                    os.remove(path)
                except Exception:
                    pass
    return None

def download_image(url: str, sku: str, img_dir: str) -> Optional[str]:
    """Baixa imagem bruta e salva como {sku}.raw.jpg."""
    if not url:
        return None

    os.makedirs(img_dir, exist_ok=True)
    raw_path = os.path.join(img_dir, f"{sku}.raw.jpg")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = PilImage.open(BytesIO(response.content)).convert("RGB")

        if img.width > MAX_DOWNLOAD_WIDTH:
            new_h = int(img.height * (MAX_DOWNLOAD_WIDTH / img.width))
            img = img.resize((MAX_DOWNLOAD_WIDTH, new_h), PilImage.Resampling.LANCZOS)
            logger.debug(f"Download redimensionado para SKU {sku}: {MAX_DOWNLOAD_WIDTH}x{new_h}px")

        img.save(raw_path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True, subsampling=2)
        if os.path.getsize(raw_path) > 0:
            logger.info(f"[DOWNLOAD] SKU {sku}: {raw_path} ({os.path.getsize(raw_path)//1024} KB)")
            return raw_path
        else:
            logger.error(f"Arquivo baixado vazio para SKU {sku}: {raw_path}")
            os.remove(raw_path)
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro HTTP ao baixar SKU {sku} ({url}): {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao processar download SKU {sku}: {e}")
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
            except Exception:
                pass
    return None

# -------------------------
# Validação / Utilitários
# -------------------------
def validate_image(image_path: str) -> bool:
    """Verifica se arquivo existe e é uma imagem válida."""
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        return False
    try:
        with PilImage.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        logger.warning(f"Arquivo corrompido/inválido: {image_path}")
        return False

def get_image_dimensions(image_path: str) -> Optional[Tuple[int, int]]:
    """Obtém dimensões da imagem."""
    if not validate_image(image_path):
        return None
    try:
        with PilImage.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Erro lendo dimensões '{image_path}': {e}")
        return None

def optimize_image(input_path: str, output_path: str,
                   max_size: Tuple[int, int] = (FINAL_SIZE, FINAL_SIZE),
                   quality: int = JPEG_QUALITY) -> bool:
    """Gera versão otimizada (JPEG quadrado menor)."""
    try:
        with PilImage.open(input_path) as img:
            img = img.convert("RGB")
            orig_size = os.path.getsize(input_path) if os.path.exists(input_path) else 0
            img.thumbnail(max_size, PilImage.Resampling.LANCZOS)
            img.save(output_path, "JPEG",
                     quality=quality, optimize=True,
                     progressive=True, subsampling=2)
            logger.info(
                f"[OPTIMIZE] {input_path} -> {output_path} "
                f"({orig_size//1024} KB -> {os.path.getsize(output_path)//1024} KB)"
            )
        return True
    except Exception as e:
        logger.error(f"Falha ao otimizar imagem '{input_path}': {e}")
        return False

# -------------------------
# Funções auxiliares de crop
# -------------------------
def _crop_subtitle(img: PILImageType) -> PILImageType:
    """Remove subtítulo inferior da imagem, se identificado."""
    arr = np.asarray(img)
    h, w, _ = arr.shape
    diff = np.abs(255 - arr).sum(axis=2)
    mask = diff > (3 * BG_TOLERANCE)
    nonwhite = mask.mean(axis=1)
    std_rows = arr.std(axis=2).mean(axis=1)
    grad = np.abs(np.diff(nonwhite, n=1, prepend=0))

    max_cut = int(h * MAX_SUBTITLE_FRACTION)
    cut = 0
    for i in range(h-1, max(h-1-max_cut, -1), -1):
        if (nonwhite[i] < TEXT_ROW_DENSITY or std_rows[i] < UNIFORM_ROW_STD) and grad[i] > 0.02:
            cut += 1
        else:
            break

    if cut > 15:
        logger.debug(f"[CROP] Subtítulo removido ({cut}px)")
        img = img.crop((0, 0, w, h-cut))
    return img

def _crop_borders(img: PILImageType) -> PILImageType:
    """Remove áreas brancas ao redor do produto."""
    arr = np.asarray(img)
    h, w, _ = arr.shape
    diff = np.abs(255 - arr).sum(axis=2)
    mask = diff > (3 * BG_TOLERANCE)

    ys, xs = np.where(mask)
    if len(xs) > 0 and len(ys) > 0:
        left = max(0, xs.min()-CROP_PADDING)
        right = min(w, xs.max()+1+CROP_PADDING)
        upper = max(0, ys.min()-CROP_PADDING)
        lower = min(h, ys.max()+1+CROP_PADDING)
        img = img.crop((left, upper, right, lower))
        logger.debug(f"[CROP] Bordas removidas: ({left}, {upper}, {right}, {lower})")
    return img

def _place_on_square(img: PILImageType, size: int = FINAL_SIZE) -> PILImageType:
    """
    Centraliza a imagem em um canvas quadrado branco,
    forçando ocupação máxima proporcional.
    """
    ratio = min(size / img.width, size / img.height)
    new_w, new_h = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((new_w, new_h), PilImage.Resampling.LANCZOS)

    canvas = PilImage.new("RGB", (size, size), (255, 255, 255))
    offx = (size - new_w) // 2
    offy = (size - new_h) // 2
    canvas.paste(img, (offx, offy))

    return canvas

def auto_crop_image(image_path: str) -> bool:
    """Pipeline de crop: remove subtítulo + bordas + ajusta para quadrado + resize final."""
    try:
        with PilImage.open(image_path) as im:
            im = im.convert("RGB")
            im = _crop_subtitle(im)
            im = _crop_borders(im)
            im = _place_on_square(im, FINAL_SIZE)

            # 🔑 garante que sempre será FINAL_SIZE x FINAL_SIZE
            im = im.resize((FINAL_SIZE, FINAL_SIZE), PilImage.Resampling.LANCZOS)

            im.save(
                image_path,
                "JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,
                subsampling=2,
            )
        logger.debug(f"[FINAL] Corte + resize aplicado em {image_path}")
        return True
    except Exception as e:
        logger.error(f"Erro ao cortar/redimensionar imagem {image_path}: {e}")
        return False

# -------------------------
# Função de alto nível
# -------------------------
def prepare_image_for_sku(sku: str, url: str, img_dir: str,
                          skip_download: bool = False) -> Tuple[Optional[str], str]:
    """
    Pipeline unificado de imagem:
      - Reutiliza otimizada existente.
      - Usa imagem bruta existente e gera otimizada.
      - Se necessário, baixa da URL e processa.
    Retorna (caminho_final, status).
    Status pode ser: reused, optimized, downloaded, missing.
    """
    os.makedirs(img_dir, exist_ok=True)
    optimized_path = os.path.join(img_dir, f"optimized_{sku}.jpg")

    # 1. Verifica se otimizada já existe
    if os.path.exists(optimized_path) and validate_image(optimized_path):
        return optimized_path, "reused"

    # 2. Procura imagem existente (bruta)
    existing = find_image_for_sku(sku, img_dir, prefer_optimized=False)
    if existing:
        if optimize_image(existing, optimized_path) and auto_crop_image(optimized_path):
            return optimized_path, "optimized"
        else:
            logger.warning(f"Falha ao otimizar arquivo existente para SKU {sku}.")

    # 3. Baixa imagem da URL se necessário
    if url and not skip_download:
        downloaded = download_image(url, sku, img_dir)
        if downloaded:
            if optimize_image(downloaded, optimized_path) and auto_crop_image(optimized_path):
                try:
                    if downloaded.endswith(".raw.jpg") and os.path.exists(downloaded):
                        os.remove(downloaded)
                except Exception:
                    pass
                return optimized_path, "downloaded"
            else:
                logger.warning(f"Falha no processamento da imagem baixada para SKU {sku}.")

    return None, "missing"
