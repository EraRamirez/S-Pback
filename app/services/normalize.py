import unicodedata


def normalize_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))
