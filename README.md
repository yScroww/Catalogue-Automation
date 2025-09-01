# Gerador de Catálogo em PDF

Este projeto é uma ferramenta de automação em Python para gerar catálogos de produtos no formato PDF. Ele utiliza dados de planilhas Excel e arquivos de imagem para criar documentos estruturados e prontos para uso. O objetivo é simplificar e agilizar o processo de criação de catálogos para a equipe comercial.

## Como Funciona a Arquitetura

O projeto foi construído com uma arquitetura modular, dividida em funções específicas para cada tarefa, o que facilita a manutenção e a expansão. O fluxo de trabalho principal é o seguinte:

- **Orquestração de Processos**: O script `main.py` atua como o controlador principal. Ele coordena as etapas, desde o carregamento dos dados até a geração final do PDF.
  
- **Gerenciamento de Dados**: O módulo `src/utils/excel.py` é responsável por ler os dados de produtos e os links de imagens a partir dos arquivos Excel. O script aplica filtros para incluir apenas produtos relevantes, como aqueles com estoque positivo e que não são promocionais.
  
- **Processamento de Imagens**: O módulo `src/utils/images.py` cuida de todas as operações com as imagens. Ele verifica se as imagens já existem localmente e, se não, as baixa, otimiza e corta automaticamente para que se ajustem ao layout do catálogo.
  
- **Criação do PDF**: A lógica de layout do documento está concentrada no `src/pdf_builder.py`. Este módulo adiciona as capas personalizadas por "Força" (ex: Food, Bebidas) e organiza os produtos em uma grade, categorizando-os por "Grupo" e "Família".
  
- **Ponto de Entrada**: O arquivo `run.py` é o ponto de partida do projeto. Ele define os caminhos de rede para os arquivos de entrada e saída, garantindo que o programa funcione corretamente em um ambiente compartilhado.

## Estrutura do Projeto

A organização dos arquivos e pastas é a seguinte:

.
├── src/
│ ├── utils/
│ │ ├── excel.py # Funções para carregar dados das planilhas.
│ │ ├── images.py # Funções para download e otimização de imagens.
│ │ └── logger.py # Configuração de logging.
│ ├── main.py # Orquestra as etapas de processamento.
│ └── pdf_builder.py # Constrói o layout do documento PDF.
├── data/
│ ├── base_imagens.xlsx # Planilha com URLs das imagens.
│ ├── produtos.xlsx # Planilha principal com dados dos produtos.
│ ├── imagens/ # Diretório para imagens processadas.
│ └── capas_forças/ # Diretório para as imagens de capa.
│ ├── capa.png
│ └── [nome_da_força].png
└── run.py # Script principal para execução e configuração.


## Dependências

O projeto utiliza as seguintes bibliotecas Python. Elas podem ser instaladas via pip:

- `pandas`
- `reportlab`
- `Pillow`
- `requests`
- `pyinstaller` (para criar o executável)

Para instalar todas as dependências de uma vez, execute o seguinte comando:

- `pip install requirements.txt`


## Como Usar

### 1. Criando o Executável

Para compilar o projeto em um executável autônomo, navegue até a pasta raiz do projeto (onde o arquivo `run.py` está localizado) e execute o comando do PyInstaller:

- `pyinstaller --onefile run.py`


O arquivo `run.exe` será gerado na pasta `dist/`.

### 2. Executando o Script

Para iniciar a geração do catálogo, execute o arquivo `run.exe`. O programa irá:

1. Carregar os dados e as imagens.
2. Gerar o `Catálogo_Nordesa.pdf` na pasta de saída especificada no `run.py`.
3. Criar um arquivo `status_catalogo.csv` que detalha quais produtos foram incluídos no catálogo.

## Solução de Problemas Comuns

### `FileNotFoundError`

Este erro indica que o programa não conseguiu encontrar um arquivo. Verifique se o caminho de rede configurado na variável `NETWORK_PATH` no arquivo `run.py` está correto e se o usuário tem permissão de acesso à pasta.