"""
Generate InnoSetup wizard bitmap images from the Octavium logo.

InnoSetup requires specific BMP sizes:
  - WizardImageFile:      164 x 314 pixels (tall left-side panel)
  - WizardSmallImageFile:  55 x  58 pixels (top-right corner)

Usage:
    python installer/generate_wizard_images.py

Outputs:
    installer/wizard_large.bmp
    installer/wizard_small.bmp
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
LOGO_PATH = PROJECT_ROOT / "assets" / "Octavium icon.png"

# InnoSetup required dimensions
LARGE_SIZE = (164, 314)
SMALL_SIZE = (55, 58)

# Branding colours (matching the Octavium blue palette)
BG_COLOR_TOP = (20, 35, 75)      # Dark navy
BG_COLOR_BOTTOM = (45, 85, 150)  # Medium blue


def create_gradient(size, color_top, color_bottom):
    """Create a vertical gradient image."""
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(size[1]):
        ratio = y / max(size[1] - 1, 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    return img


def generate_large_wizard():
    """Generate the 164x314 wizard side panel image."""
    img = create_gradient(LARGE_SIZE, BG_COLOR_TOP, BG_COLOR_BOTTOM)

    # Load and resize the logo to fit the width with padding
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo_width = LARGE_SIZE[0] - 24  # 12px padding each side
    logo_height = int(logo.height * (logo_width / logo.width))
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

    # Center the logo vertically in the upper portion
    x_offset = (LARGE_SIZE[0] - logo_width) // 2
    y_offset = 30

    # Composite logo onto gradient
    img.paste(logo, (x_offset, y_offset), logo)

    # Add tagline text below the logo
    draw = ImageDraw.Draw(img)
    tagline = "Making\nmusic\naccessible"

    # Try to use a nice font, fall back to default
    font_size = 16
    try:
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    text_y = y_offset + logo_height + 20
    draw.multiline_text(
        (LARGE_SIZE[0] // 2, text_y),
        tagline,
        fill=(180, 210, 255),
        font=font,
        anchor="ma",
        align="center",
        spacing=4,
    )

    out_path = SCRIPT_DIR / "wizard_large.bmp"
    img.convert("RGB").save(out_path, "BMP")
    print(f"Created: {out_path}")


def generate_small_wizard():
    """Generate the 55x58 wizard header image."""
    img = create_gradient(SMALL_SIZE, BG_COLOR_TOP, BG_COLOR_BOTTOM)

    # Load and resize the icon to fit
    logo = Image.open(LOGO_PATH).convert("RGBA")
    icon_size = min(SMALL_SIZE) - 8  # 4px padding each side
    logo = logo.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

    x_offset = (SMALL_SIZE[0] - icon_size) // 2
    y_offset = (SMALL_SIZE[1] - icon_size) // 2

    img.paste(logo, (x_offset, y_offset), logo)

    out_path = SCRIPT_DIR / "wizard_small.bmp"
    img.convert("RGB").save(out_path, "BMP")
    print(f"Created: {out_path}")


if __name__ == "__main__":
    print("Generating InnoSetup wizard images...")
    print(f"  Logo source: {LOGO_PATH}")
    generate_large_wizard()
    generate_small_wizard()
    print("Done!")
