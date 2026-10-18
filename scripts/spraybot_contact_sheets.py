"""Build one compact image sheet per generator from a validation run.

The full resolution PNGs and Blender files stay in each seed directory.
This sheet is only an index for quickly reviewing shape variation.
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path, help="output directory from spraybot_validate.py")
    args = parser.parse_args()
    run = args.run.resolve()
    info = json.loads((run / "run_info.json").read_text(encoding="utf-8"))
    sheet_dir = run / "contact_sheets"
    sheet_dir.mkdir(exist_ok=True)
    width, height, columns = 192, 192, 4
    cell_width, cell_height = width * 2 + 12, height + 42
    for index, name in enumerate(info["generators"]):
        short = name.removeprefix("spraybot:").removeprefix("workpiece:").rsplit(".", 1)[-1]
        seeds = info["seeds"]
        rows = (len(seeds) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * cell_width, rows * cell_height + 34), "#f4f5f7")
        draw = ImageDraw.Draw(sheet)
        draw.text((10, 10), f"{index:03d} {short}", fill="#172238")
        for cell, seed in enumerate(seeds):
            sample = run / f"{index:03d}_{short}" / f"seed_{seed:04d}"
            x = (cell % columns) * cell_width
            y = (cell // columns) * cell_height + 34
            draw.text((x + 6, y + 5), f"seed {seed:04d}", fill="#172238")
            for view in range(2):
                path = sample / f"view_{view}.png"
                if path.is_file():
                    with Image.open(path) as source:
                        thumbnail = source.convert("RGB").resize((width, height))
                    sheet.paste(thumbnail, (x + 6 + view * width, y + 26))
                else:
                    draw.text((x + 12 + view * width, y + 75), "pending / failed", fill="#a22b2b")
        sheet.save(sheet_dir / f"{index:03d}_{short}.jpg", quality=88)
    print(f"wrote {len(info['generators'])} contact sheets to {sheet_dir}")


if __name__ == "__main__":
    main()
