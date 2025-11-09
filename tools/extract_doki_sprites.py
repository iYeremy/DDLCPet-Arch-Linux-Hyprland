#!/usr/bin/env python3
from pathlib import Path

from PIL import Image

ATLAS = Path("json_test_paginainspiracion/Doki Doki_texture_0.png")
OUTPUTS = {
    "idle.png": (166, 262, 307, 423),  # personaje con brazo levantado
    "walk.png": (314, 262, 455, 421),  # personaje con brazos abajo
}


def main() -> None:
    atlas = Image.open(ATLAS).convert("RGBA")
    for filename, box in OUTPUTS.items():
        crop = atlas.crop(box)
        out_path = Path("assets") / filename
        crop.save(out_path)
        print(f"Guardado {out_path} ({crop.size[0]}x{crop.size[1]})")


if __name__ == "__main__":
    main()
