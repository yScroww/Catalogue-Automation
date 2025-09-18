# src/main.py
import os
import pandas as pd
from typing import List, Dict, Tuple

from src.pdf_builder import create_catalog_pdf
from src.utils.logger import get_logger
from src.utils.excel import load_product_data, load_image_links
from src.utils import images

logger = get_logger(__name__)


def prepare_dataframe(excel_path: str, img_excel_path: str) -> Tuple[pd.DataFrame, str, str]:
    """Carrega e prepara os dados de produtos e links de imagens."""
    df, c_sku, c_nome, c_cat, c_img = load_product_data(excel_path)
    img_links_df = load_image_links(img_excel_path)

    # Garante tipo SKU string
    df[c_sku] = df[c_sku].astype(str).str.replace(r"\.0$", "", regex=True)
    if "SKU" in img_links_df.columns:
        img_links_df["SKU"] = img_links_df["SKU"].astype(str).str.replace(r"\.0$", "", regex=True)

    df = df.merge(img_links_df, how="left", left_on=c_sku, right_on="SKU")

    # Coluna de URL final
    if c_img and "ImageURL" in df.columns:
        df["FinalImageURL"] = df[c_img].fillna(df["ImageURL"])
    else:
        df["FinalImageURL"] = df.get("ImageURL", pd.Series(dtype=str))

    # Filtros
    if "Estoque" in df.columns:
        df = df[df["Estoque"] > 0]
    if "Promocional" in df.columns:
        df = df[df["Promocional"].astype(str).str.upper().str.strip() == "NAO"]

    # Padronização de nomes
    if "Nome Força" in df.columns:
        df["Nome Força"] = df["Nome Força"].str.strip().str.title()
        df = df.rename(columns={"Nome Força": "Nome da Força"})

    # Garantir colunas de agrupamento
    for col, default in [("Grupo", "Não Classificado"), ("Familia", "Não Classificada")]:
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default)

    return df, c_sku, c_nome


def main(
    excel_path: str,
    img_excel_path: str,
    imagens_path: str,
    capas_path: str,
    output_file: str,
    include_no_image: bool = False,
    max_products: int = 0,
    skip_download: bool = False,
) -> None:
    """Pipeline principal de construção do catálogo em PDF + relatório CSV."""
    df, c_sku, c_nome = prepare_dataframe(excel_path, img_excel_path)

    if max_products > 0:
        df = df.head(max_products)

    products: List[Dict] = []
    missing_images: List[Dict] = []

    logger.info(f"Processando {len(df)} produtos...")

    for _, row in df.iterrows():
        info = row.to_dict()
        sku = str(info[c_sku]).strip()
        final_url = str(info.get("FinalImageURL", "")).strip()

        info["SKU"] = sku
        info["Nome do Produto"] = str(info.get(c_nome, "")).strip()

        # Processamento da imagem (com cache inteligente)
        try:
            img_result = images.prepare_image_for_sku(
                sku, final_url, imagens_path, skip_download=skip_download
            )
            img_path, status = img_result if isinstance(img_result, tuple) else (img_result, "")
        except Exception as e:
            logger.error(f"Erro ao processar imagem do SKU {sku}: {e}")
            img_path = None
            status = "erro"

        info["image_path"] = img_path
        info["image_status"] = status

        if img_path:
            products.append(info)
            logger.debug(f"Imagem processada para SKU {sku}")
        else:
            missing_images.append(info)
            logger.warning(f"Sem imagem para SKU {sku}")

    # Gera PDF apenas com produtos com imagem
    if not products:
        logger.warning("Nenhum produto com imagem disponível para gerar catálogo.")
    else:
        # Ordenação refinada
        products.sort(
            key=lambda x: (
                x.get("Grupo", ""),
                x.get("Familia", ""),
                x.get("Nome do Produto", ""),
                x.get("SKU", ""),
            )
        )

        create_catalog_pdf(products, output_file, capas_path)
        logger.info(f"✅ Catálogo gerado: {output_file}")

    # --- Relatório CSV de TODOS os produtos ---
    logger.info("Gerando relatório CSV geral de SKUs...")
    df_report = df.copy()
    df_report["Inserido no Catálogo"] = df_report[c_sku].astype(str).isin(
        [p["SKU"] for p in products]
    ).map({True: "SIM", False: "NAO"})

    csv_path = os.path.splitext(output_file)[0] + "_relatorio.csv"
    df_report[[c_sku, c_nome, "Inserido no Catálogo"]].to_csv(
        csv_path, sep=";", index=False, encoding="utf-8-sig"
    )
    logger.info(f"📄 Relatório completo salvo em: {csv_path}")

    # --- Relatório CSV de produtos sem imagem (opcional) ---
    if missing_images and include_no_image:
        missing_df = pd.DataFrame(missing_images)
        csv_path = os.path.splitext(output_file)[0] + "_sem_imagem.csv"
        missing_df.to_csv(csv_path, sep=";", index=False, encoding="utf-8-sig")
        logger.warning(f"⚠️ {len(missing_images)} produtos ficaram de fora. Relatório salvo em: {csv_path}")
