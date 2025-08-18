
# Catálogo de Produtos — Automação em Python

Este projeto gera um catálogo em **PowerPoint (.pptx)** a partir de uma **planilha Excel** e de uma **pasta com imagens** organizadas por **SKU**.

## Estrutura criada
```
projeto_catalogo_python/
├─ build_catalog.py
├─ produtos_exemplo.xlsx
├─ template_catalogo.pptx        ← cópia do seu PPTX enviado (base/template)
├─ imagens/
│  ├─ 12479825.png
│  ├─ 12581976.png
│  ├─ 12338492.png
│  └─ 12571524.png
└─ README_passo_a_passo.md
```

## Requisitos
- Python 3.9+
- Instale as dependências:
```
pip install pandas python-pptx pillow
```

## Como executar
Na pasta do projeto, rode:
```
python build_catalog.py --excel produtos_exemplo.xlsx --imagens ./imagens --template template_catalogo.pptx --out catalogo_gerado.pptx
```
Você pode ajustar o layout com:
```
--cols 3 --rows 3 --margem 0.4 --topo 1.1 --base 0.3 --hgap 0.25 --vgap 0.25
```

## Planilha (colunas)
- **SKU** (obrigatório)
- **Nome** (obrigatório)
- **Categoria** (obrigatório) — define em qual seção o produto entra; cada categoria gera uma ou mais páginas.
- **ImagemArquivo** (opcional) — caminho direto da imagem; se vazio, o script procura por `SKU.jpg/png/webp` na pasta `imagens/`.
- **Ativo** (opcional) — se `True/Sim/Ativo`, o item entra; caso contrário, fica de fora.

> **Remover um produto** da planilha automaticamente reflowa os demais: é só rodar de novo e o grid é recriado do zero.  
> **Distância padrão** entre itens vem de `hgap`/`vgap`.  
> **Grid**: defina `cols` e `rows` conforme o visual desejado.

## Dicas
- Mantenha as imagens quadradas ou com fundo transparente para um acabamento mais limpo.
- Nomeie arquivos exatamente com o SKU (ex.: `12479825.jpg`) para facilitar.
- Personalize o **template_catalogo.pptx**: fontes, cores, plano de fundo. O script usa o layout **em branco** do template.

## Edição de layout avançada
Se quiser:
- Título com logo — edite no slide master do template e reduza `--topo`.
- Fonte e cores — altere diretamente no `build_catalog.py` (funções `add_textbox` e `add_product_tile`).

Se precisar, posso adaptar o script para:
- Paginação com numeração/rodapé.
- Inserir preço e descrição no tile.
- Gerar sumário por categoria.
- Exportar PDF automaticamente.
