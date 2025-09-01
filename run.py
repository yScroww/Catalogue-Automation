import os
import sys
from src.main import main

# Define os caminhos de rede para as planilhas e a pasta de imagens
NETWORK_PATH = r"\\192.168.0.7\Depto Comercial\04-Habilidades para vencer\05-Catálago\Gerador de Catálogo"
EXCEL_PATH = os.path.join(NETWORK_PATH, "data", "produtos.xlsx")
IMG_EXCEL_PATH = os.path.join(NETWORK_PATH, "data", "base_imagens.xlsx")
IMAGENS_PATH = os.path.join(NETWORK_PATH, "data", "imagens")
CAPAS_PATH = os.path.join(NETWORK_PATH, "data", "capas_forças")

if __name__ == '__main__':
    try:
        # Chama a função principal do seu código, passando os caminhos de rede
        # como argumentos, incluindo a pasta de imagens e capas.
        main(EXCEL_PATH, IMG_EXCEL_PATH, IMAGENS_PATH, CAPAS_PATH)

    except FileNotFoundError as e:
        print(f"Erro: Arquivo não encontrado. Verifique se o caminho de rede está correto e se o arquivo existe: {e}")
        input("Pressione Enter para fechar...")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        input("Pressione Enter para fechar...")