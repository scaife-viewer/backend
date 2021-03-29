import unicodedata

import regex


UNICODE_MARK_CATEGORY_REGEX = regex.compile(r"\p{M}")


def nfkc(s):
    return unicodedata.normalize("NFKC", s)


def nfd(s):
    return unicodedata.normalize("NFD", s)


def strip_marks(s):
    """
    https://unicode.org/reports/tr18/#General_Category_Property
    """
    cps = nfd(s)
    return nfkc(UNICODE_MARK_CATEGORY_REGEX.sub("", cps))


def normalize_string(s):
    """
    Strip marks and return the case-folded representation of string
    """
    return strip_marks(s).lower()
