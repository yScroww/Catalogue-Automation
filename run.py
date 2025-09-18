# run.py
import os
from src.main import main
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = r"Z:\04-Habilidades para vencer\05-Catálago\Gerador de Catálogo\data"

EXCEL_PATH = os.path.join(BASE_DIR, "produtos.xlsx")
IMG_EXCEL_PATH = os.path.join(BASE_DIR, "base_imagens.xlsx")
IMAGENS_PATH = os.path.join(BASE_DIR, "imagens")
CAPAS_PATH = os.path.join(BASE_DIR, "capas_forças")

OUTPUT_FILE = "Catalogo_Nordesa.pdf"
OUTPUT_DIR = r"Z:\04-Habilidades para vencer\05-Catálago"

if __name__ == "__main__":
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        final_output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

        logger.info("🚀 Iniciando a geração do catálogo...")
        main(
            excel_path=EXCEL_PATH,
            img_excel_path=IMG_EXCEL_PATH,
            imagens_path=IMAGENS_PATH,
            capas_path=CAPAS_PATH,
            output_file=final_output_path,
        )
        logger.info(f"🎉 Concluído! Catálogo salvo em: {final_output_path}")

    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}", exc_info=True)
