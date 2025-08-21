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
            img = img.resize((MAX_WIDTH, height), Image.LANCZOS)
            logger.info(f"Imagem do SKU {sku} redimensionada para {MAX_WIDTH}x{height} pixels.")
        
        img.save(file_path, 'JPEG', quality=95)
        
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


def optimize_image(input_path: str, output_path: str, max_size=(800, 800), quality=90) -> bool:
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


def auto_crop_image(
    image_path: str,
    padding: int = 12,
    bg_tolerance: int = 20,
    text_row_density: float = 0.10,
    uniform_row_std: float = 5.0,
    max_subtitle_fraction: float = 0.30,
    final_square_size: int = 800
) -> bool:
    """
    Corta dinamicamente a faixa de “subtítulo” quando presente e remove bordas,
    sem cortar imagens que não precisam. Em seguida, exporta em formato quadrado.

    Estratégia:
      1) Converter para RGB e medir, por linha, (a) densidade de pixels "não-fundo"
         (distantes do branco) e (b) uniformidade da linha (desvio padrão baixo = faixa sólida).
      2) Subir a partir da base enquanto a linha tiver:
            - densidade baixa (apenas texto fino) OU
            - for muito uniforme (faixa sólida),
         limitado por 'max_subtitle_fraction' da altura.
      3) Remover bordas laterais/topo via bounding-box de pixels "não-fundo".
      4) Colar resultado em um canvas quadrado para uniformizar o layout no PDF.

    Parâmetros ajustáveis:
      - bg_tolerance: tolerância para considerar um pixel como “fundo quase branco”.
      - text_row_density: densidade máxima para classificar linha com “texto fino”.
      - uniform_row_std: se std somado da linha for menor que este valor, tratamos como faixa sólida.
      - max_subtitle_fraction: proteção para não cortar demais (percentual da altura).
      - final_square_size: tamanho final do quadrado de saída (ex.: 800).
    """
    try:
        with Image.open(image_path) as im:
            im = im.convert('RGB')
            rgb = _to_numpy_rgb(im)
            h, w, _ = rgb.shape

            # 1) Métricas por linha
            nonwhite_ratio, row_std_sum = _compute_nonwhite_and_std(rgb, bg_tolerance)

            # 2) Corte dinâmico do subtítulo (de baixo para cima)
            max_cut_rows = int(h * max_subtitle_fraction)
            cut_from_bottom = 0
            for i in range(h - 1, max(h - 1 - max_cut_rows, -1), -1):
                line_is_sparse_text = nonwhite_ratio[i] < text_row_density
                line_is_uniform_band = row_std_sum[i] < uniform_row_std
                if line_is_sparse_text or line_is_uniform_band:
                    cut_from_bottom += 1
                else:
                    break

            if cut_from_bottom > 0:
                logger.info(f"Corte de subtítulo detectado: {cut_from_bottom} linhas removidas (~{100*cut_from_bottom/h:.1f}% da altura).")
                im = im.crop((0, 0, w, h - cut_from_bottom))
                rgb = _to_numpy_rgb(im)  # atualiza matriz após crop
                h, w, _ = rgb.shape
                nonwhite_ratio, _ = _compute_nonwhite_and_std(rgb, bg_tolerance)

            # 3) Remoção de bordas (bbox de conteúdo != fundo)
            arr = rgb.astype(np.int16)
            l1 = np.abs(255 - arr).sum(axis=2)
            mask_nonwhite = l1 > (3 * bg_tolerance)

            bbox = _bbox_from_mask(mask_nonwhite, padding=padding, width=w, height=h)
            if bbox:
                im = im.crop(bbox)
            else:
                logger.debug("BBox não encontrada, mantendo imagem como está.")

            # 4) Padroniza para quadrado
            im_square = _paste_on_square(im, size=final_square_size, bg=(255, 255, 255))
            im_square.save(image_path, "JPEG", quality=95, optimize=True)

        return True

    except Exception as e:
        logger.error(f"Erro ao cortar a imagem '{image_path}': {e}")
        return False
