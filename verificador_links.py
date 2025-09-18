import pandas as pd
import os
import requests
from src.utils.logger import get_logger
from src.utils.excel import load_product_data, load_image_links

logger = get_logger(__name__)

# --- CONFIGURAÇÃO ---
EXCEL_PATH = r"data/produtos.xlsx"
IMG_EXCEL_PATH = r"data/base_imagens.xlsx"
IMAGENS_PATH = r"data/imagens" # Pasta com imagens já processadas
# --------------------

def verificar_links_ausentes():
    # 1. Carrega e filtra os SKUs da mesma forma que o main.py
    df, c_sku, _, _, c_img = load_product_data(EXCEL_PATH)
    img_links_df = load_image_links(IMG_EXCEL_PATH)

    df[c_sku] = df[c_sku].astype(str).str.replace(r'\.0$', '', regex=True)
    if 'SKU' in img_links_df.columns:
        img_links_df['SKU'] = img_links_df['SKU'].astype(str).str.replace(r'\.0$', '', regex=True)
    
    df = df.merge(img_links_df, how="left", left_on=c_sku, right_on="SKU")
    df["FinalImageURL"] = df[c_img].fillna(df["ImageURL"]) if c_img and 'ImageURL' in df.columns else (df.get("ImageURL", pd.Series(dtype=str)))

    if 'Estoque' in df.columns: df = df[df['Estoque'] > 0]
    if 'Promocional' in df.columns: df = df[df['Promocional'].str.upper().str.strip() == 'NAO']
    
    skus_necessarios = set(df[c_sku])
    
    # 2. Pega a lista de imagens que já temos
    imagens_existentes = {os.path.splitext(f)[0] for f in os.listdir(IMAGENS_PATH)}
    
    # 3. Encontra os SKUs que faltam
    skus_ausentes = skus_necessarios - imagens_existentes
    
    print(f"Total de SKUs ausentes a serem verificados: {len(skus_ausentes)}")
    print("-" * 50)

    # 4. Testa a URL de cada SKU ausente
    df_ausentes = df[df[c_sku].isin(skus_ausentes)]
    
    for _, row in df_ausentes.iterrows():
        sku = row[c_sku]
        url = row.get('FinalImageURL')

        if not url or pd.isna(url):
            print(f"SKU: {sku} - STATUS: Falha (URL está VAZIA na planilha)")
            continue

        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type:
                    print(f"SKU: {sku} - STATUS: Sucesso (URL válida e aponta para uma imagem)")
                else:
                    print(f"SKU: {sku} - STATUS: Falha (URL válida, mas não aponta para uma imagem. Tipo: {content_type})")
            else:
                print(f"SKU: {sku} - STATUS: Falha (URL com erro: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"SKU: {sku} - STATUS: Falha (Erro de conexão: {e})")

if __name__ == "__main__":
    verificar_links_ausentes()