# run.py
import os
from src.main import main
from src.utils.logger import get_logger
import dotenv

dotenv.load_dotenv(override=True)

logger = get_logger(__name__)

BASE_DIR = os.getenv("BASE_DIR", "")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "")

EXCEL_PATH = os.getenv("EXCEL_PATH", os.path.join(BASE_DIR, "produtos.xlsx"))
IMG_EXCEL_PATH = os.getenv("IMG_EXCEL_PATH", os.path.join(BASE_DIR, "base_imagens.xlsx"))
IMAGENS_PATH = os.getenv("IMAGENS_PATH", os.path.join(BASE_DIR, "imagens"))
CAPAS_PATH = os.getenv("CAPAS_PATH", os.path.join(BASE_DIR, "capas_forças"))

OUTPUT_FILE = os.getenv("OUTPUT_FILE", "Catalogo Nordesa.pdf")


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
