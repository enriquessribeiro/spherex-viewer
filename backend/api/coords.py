"""Interpretação de coordenadas digitadas pelo usuário (sem chamada externa)."""

from __future__ import annotations

import re

import astropy.units as u
from astropy.coordinates import SkyCoord

_NUMERIC = re.compile(r"^\s*([+-]?\d+(?:\.\d*)?)\s*[,\s]\s*([+-]?\d+(?:\.\d*)?)\s*$")
_SEXAGESIMAL = re.compile(r"\d+\s*[h:]\s*\d+|\d+\s+\d+\s+\d+(\.\d*)?\s+[+-]?\d+\s+\d+")


def parse_coordinates(text: str) -> tuple[float, float] | None:
    """'133.795 -7.245', '133.795,-7.245' ou '08h55m10.8s -07d14m42.5s' → (ra, dec) em graus."""
    match = _NUMERIC.match(text)
    if match:
        return float(match.group(1)), float(match.group(2))
    if _SEXAGESIMAL.search(text):
        try:
            coord = SkyCoord(text, unit=(u.hourangle, u.deg))
        except ValueError:
            return None
        return float(coord.ra.deg), float(coord.dec.deg)
    return None
