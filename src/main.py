import argparse
from catalog_builder import build_catalog
from layout_config import get_layout_config, LayoutType
from utils.logger import get_logger

logger = get_logger(__name__)

def parse_args():
    """Configura e parseia argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Gerador de Catálogo em PowerPoint",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Argumentos principais
    parser.add_argument("--excel", default="data/products.xlsx",
                      help="Planilha com dados dos produtos")
    parser.add_argument("--img-excel", default="data/imagens/base_imagens.xlsx",
                      help="Planilha com links das imagens")
    parser.add_argument("--imagens", default="data/imagens",
                      help="Pasta onde as imagens serão salvas")
    parser.add_argument("--template", default="template/template_catalogo.pptx",
                      help="Arquivo PPTX base para o template")
    parser.add_argument("--out", default="catalogo_gerado.pptx",
                      help="Arquivo de saída do catálogo")
    
    # Opções de layout
    parser.add_argument("--layout", choices=["default", "compact", "large"], default="default",
                      help="Tipo de layout do catálogo")
    parser.add_argument("--cols", type=int,
                      help="Número de colunas por slide (sobrescreve layout)")
    parser.add_argument("--rows", type=int,
                      help="Número de linhas por slide (sobrescreve layout)")
    
    # Opções de processamento
    parser.add_argument("--skip-download", action="store_true",
                      help="Pular download de imagens (usar apenas locais)")
    parser.add_argument("--include-no-image", action="store_true",
                      help="Incluir produtos sem imagem disponível")
    parser.add_argument("--max-products", type=int, default=0,
                      help="Número máximo de produtos a processar (0 para todos)")
    
    return parser.parse_args()

def main():
    try:
        args = parse_args()
        
        # Mapeia layout type
        layout_map = {
            "default": LayoutType.DEFAULT,
            "compact": LayoutType.COMPACT,
            "large": LayoutType.LARGE_IMAGES
        }
        
        # Carrega configuração de layout
        layout_config = get_layout_config(layout_map[args.layout])
        
        # Sobrescreve cols/rows se especificado
        if args.cols:
            layout_config['GRID_COLS'] = args.cols
        if args.rows:
            layout_config['GRID_ROWS'] = args.rows
        
        logger.info(f"Iniciando geração do catálogo com layout {args.layout}")
        build_catalog(args, layout_config)
        
    except Exception as e:
        logger.error(f"Erro fatal ao gerar catálogo: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()