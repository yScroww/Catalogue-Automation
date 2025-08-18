from pptx.util import Inches, Pt
from enum import Enum

class LayoutType(Enum):
    DEFAULT = 1
    COMPACT = 2
    LARGE_IMAGES = 3

# Configurações padrão
FONT_NAME = "Calibri"

def get_layout_config(layout_type: LayoutType = LayoutType.DEFAULT) -> dict:
    """Retorna configurações de layout baseadas no tipo selecionado."""
    configs = {
        LayoutType.DEFAULT: {
            'GRID_COLS': 3,
            'GRID_ROWS': 3,
            'MARGEM': Inches(0.4),
            'TOPO': Inches(1.1),
            'BASE': Inches(0.3),
            'HGAP': Inches(0.25),
            'VGAP': Inches(0.25),
            'TITLE_FONT_SIZE': Pt(28),
            'PRODUCT_NAME_FONT_SIZE': Pt(14),
            'SKU_FONT_SIZE': Pt(12),
            'IMAGE_PADDING': Inches(0.08)
        },
        LayoutType.COMPACT: {
            'GRID_COLS': 4,
            'GRID_ROWS': 4,
            'MARGEM': Inches(0.3),
            'TOPO': Inches(0.9),
            'BASE': Inches(0.2),
            'HGAP': Inches(0.15),
            'VGAP': Inches(0.15),
            'TITLE_FONT_SIZE': Pt(24),
            'PRODUCT_NAME_FONT_SIZE': Pt(12),
            'SKU_FONT_SIZE': Pt(10),
            'IMAGE_PADDING': Inches(0.05)
        },
        LayoutType.LARGE_IMAGES: {
            'GRID_COLS': 2,
            'GRID_ROWS': 2,
            'MARGEM': Inches(0.5),
            'TOPO': Inches(1.2),
            'BASE': Inches(0.4),
            'HGAP': Inches(0.3),
            'VGAP': Inches(0.3),
            'TITLE_FONT_SIZE': Pt(32),
            'PRODUCT_NAME_FONT_SIZE': Pt(16),
            'SKU_FONT_SIZE': Pt(12),
            'IMAGE_PADDING': Inches(0.1)
        }
    }
    return configs.get(layout_type, configs[LayoutType.DEFAULT])