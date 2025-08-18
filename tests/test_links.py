from src.utils.excel import load_product_data, load_image_links

def test_links(produtos_path="data/produtos.xlsx", imagens_path="data/base_imagens.xlsx"):
    df_prod, c_sku, c_nome, c_cat, c_img = load_product_data(produtos_path)
    df_links = load_image_links(imagens_path)
    df_links = df_links.drop_duplicates(subset=["SKU"], keep="first")

    # Left join
    df = df_prod.merge(df_links, how="left", left_on=c_sku, right_on="SKU")

    total = len(df)
    com_link = df["ImageURL"].notna().sum()
    sem_link = total - com_link

    print(f"Total de produtos: {total}")
    print(f"Produtos com link na base_imagens: {com_link}")
    print(f"Produtos SEM link na base_imagens: {sem_link}")

    # Lista SKUs sem link
    faltando = df[df["ImageURL"].isna()][c_sku].tolist()
    if faltando:
        print("\nSKUs sem link:")
        for sku in faltando:
            print("  -", sku)

if __name__ == "__main__":
    test_links()
