from underthesea import word_tokenize

def tokenize_text(text: str) -> str:
    tokens = word_tokenize(text)
    return " ".join(tokens)
