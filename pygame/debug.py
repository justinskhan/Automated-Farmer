def print_grid(level):

    print(f"\n=== LEVEL: {level.name} (#{level.number}) ===")
    print(f"Grid: {level.rows}x{level.cols}")

    # Print grid state to console 
    for r, row in enumerate(level.tiles):
        line = ""
        for c, tile in enumerate(row):
            # Crop progress -> H = harvested, # = grown, * = growing
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