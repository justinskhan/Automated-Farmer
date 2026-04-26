import sys

_IS_BROWSER = sys.platform in ("emscripten", "wasi")


def print_grid(level):
    if _IS_BROWSER:
        return

    print(f"\n=== LEVEL: {level.name} (#{level.number}) ===")
    print(f"Grid: {level.rows}x{level.cols}")

    for r, row in enumerate(level.tiles):
        line = ""
        for c, tile in enumerate(row):
            if tile.crop:
                if tile.crop.harvested:
                    line += "| H | "
                elif tile.crop.grown:
                    line += "| # | "
                else:
                    line += "| * | "
            elif tile.walkable:
                line += "| . | "
            else:
                line += "| X | "
        
        print(f"Row {r}: {line}")
    print()