import unicodedata


VARIA = "\u0300"
OXIA = "\u0301"
PERISPOMENI = "\u0342"

PSILI = "\u0313"
DASIA = "\u0314"


ACCENTS = [VARIA, OXIA, PERISPOMENI]
BREATHING = [PSILI, DASIA]

ACCENTS_AND_BREATHING = ACCENTS + BREATHING


def nfc(s):
    return unicodedata.normalize("NFC", s)


def nfd(s):
    return unicodedata.normalize("NFD", s)


def strip_accents(s, character_set=None):
    return nfc("".join(cp for cp in nfd(s) if cp not in ACCENTS_AND_BREATHING))


def normalize_greek(s):
    """
    Strip accent and breathing marks and return case-folded
    representation of string
    """
    return strip_accents(s).lower()
