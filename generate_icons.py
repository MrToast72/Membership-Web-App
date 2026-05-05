#!/usr/bin/env python3
"""
Generate app icons from source GoldIcon.png
Creates PNG and ICO versions with proper aspect ratio and padding
"""
import sys
from pathlib import Path
from PIL import Image

def detect_background_color(img):
    """Detect if background is likely white or black"""
    if img.mode != 'RGBA':
        img_rgba = img.convert('RGBA')
    else:
        img_rgba = img
    
    pixels = list(img_rgba.getdata())
    sample_size = min(1000, len(pixels))
    corners = []
    
    width, height = img.size
    corner_pixels = [
        img_rgba.getpixel((0, 0)),
        img_rgba.getpixel((width-1, 0)),
        img_rgba.getpixel((0, height-1)),
        img_rgba.getpixel((width-1, height-1))
    ]
    
    avg_r = sum(p[0] for p in corner_pixels) / 4
    avg_g = sum(p[1] for p in corner_pixels) / 4
    avg_b = sum(p[2] for p in corner_pixels) / 4
    
    brightness = (avg_r + avg_g + avg_b) / 3
    return (255, 255, 255, 0) if brightness > 127 else (0, 0, 0, 0)

def generate_icons(source_path, output_dir):
    """Generate app icons from source image"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not Path(source_path).exists():
        print(f"Source icon not found: {source_path}")
        return False
    
    img = Image.open(source_path)
    
    bg_color = detect_background_color(img)
    print(f"Detected background color: RGBA{bg_color}")
    
    icon_sizes = {
        'app_icon.png': (256, 256),
        'app_icon_64.png': (64, 64),
        'app_icon_32.png': (32, 32),
    }
    
    for filename, size in icon_sizes.items():
        output_path = output_dir / filename
        
        new_img = Image.new('RGBA', size, bg_color)
        
        img_ratio = img.width / img.height
        target_ratio = size[0] / size[1]
        
        if img_ratio > target_ratio:
            new_width = size[0]
            new_height = int(size[0] / img_ratio)
        else:
            new_height = size[1]
            new_width = int(size[1] * img_ratio)
        
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        x_offset = (size[0] - new_width) // 2
        y_offset = (size[1] - new_height) // 2
        new_img.paste(resized, (x_offset, y_offset), resized if resized.mode == 'RGBA' else None)
        
        new_img.save(output_path)
        print(f"Created: {output_path}")
    
    ico_path = output_dir / 'app_icon.ico'
    img.save(ico_path, format='ICO', sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
    print(f"Created: {ico_path}")
    
    return True

if __name__ == '__main__':
    source = Path(__file__).parent / 'GoldIcon.png'
    output = Path(__file__).parent / 'app' / 'static' / 'assets'
    
    if len(sys.argv) > 1:
        source = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output = Path(sys.argv[2])
    
    generate_icons(source, output)
