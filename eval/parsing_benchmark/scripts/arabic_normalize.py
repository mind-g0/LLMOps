import re
import unicodedata
 
# Harakat (diacritics): fatha, damma, kasra, sukun, shadda, tanwin, etc.
_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]")
 
# Tatweel / kashida (elongation character) — purely visual, never content.
_TATWEEL = re.compile(r"\u0640")
 
# Alef variants -> bare alef (أ إ آ ٱ ء-seated forms -> ا)
_ALEF_VARIANTS = re.compile(r"[\u0622\u0623\u0625\u0671]")
 
_ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
 
 
def normalize_arabic(text: str, strip_diacritics: bool = True) -> str:
    if not text:
        return text
 
    text = unicodedata.normalize("NFC", text)
    text = _TATWEEL.sub("", text)
    text = _ALEF_VARIANTS.sub("\u0627", text)  # -> ا
    text = text.translate(_ARABIC_INDIC_DIGITS)
 
    if strip_diacritics:
        text = _DIACRITICS.sub("", text)
 
    text = re.sub(r"\s+", " ", text).strip()
    return text