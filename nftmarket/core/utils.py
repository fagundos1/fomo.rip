import bleach


WORD_LIMIT = 48


def fix_long_word(word):
    if len(word) > WORD_LIMIT:
        word = f'<span title="{word}">{word[:WORD_LIMIT]}...</span>'
    return word


def fix_words(text):
    text = ' '.join(map(fix_long_word, text.split()))
    return text


def clean_text(text):
    text = bleach.clean(text, tags=[], strip=True)
    return text
