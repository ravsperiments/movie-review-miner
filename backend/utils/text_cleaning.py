import unicodedata

def clean_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",  # non-breaking space
    }

    for src, target in replacements.items():
        text = text.replace(src, target)

    # Normalize accents and other unicode artifacts (optional)
    text = unicodedata.normalize("NFKC", text)

    return text.strip()
