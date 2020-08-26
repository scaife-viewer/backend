import re


def atoi(s):
    return int(s) if s.isdigit() else s


def natural_keys(s):
    return tuple([atoi(c) for c in re.split(r"(\d+)", s)])
