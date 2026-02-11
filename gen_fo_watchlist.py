import pprint


def parse_fo_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    tokens = [t for t in text.split(",") if t]

    groups = {}
    current_group = "ROOT"
    for tok in tokens:
        tok = tok.strip()
        if tok.startswith("###"):
            current_group = tok.lstrip("#").strip()
            groups.setdefault(current_group, [])
        else:
            groups.setdefault(current_group, []).append(tok)

    return groups


def main():
    path = r"C:\Users\Admin\Downloads\_F&O (Sector_Wise) (1).txt"
    groups = parse_fo_file(path)

    # Convert to a simpler Python literal for inspection
    print("Parsed groups:\n")
    pprint.pprint(groups)


if __name__ == "__main__":
    main()

