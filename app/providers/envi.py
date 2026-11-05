"""Remote ENVI cube access through HTTP byte ranges.

PDS archives serve M3 (Imaging node) and CRISM (Geosciences node) cubes as raw
ENVI/PDS3 images with detached headers. Both servers honour ``Range``
requests (verified: HTTP 206), so a small window can be read without
downloading multi-GB cubes. Only BIL and BSQ layouts are needed here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from app.providers.http import HttpClient, ProviderError

ENVI_DTYPES = {1: "u1", 2: "i2", 3: "i4", 4: "f4", 5: "f8", 12: "u2", 13: "u4", 14: "i8", 15: "u8"}


@dataclass
class EnviHeader:
    samples: int
    lines: int
    bands: int
    data_type: int
    interleave: str
    byte_order: int = 0
    header_offset: int = 0
    ignore_value: float | None = None
    wavelengths: list[float] = field(default_factory=list)
    band_names: list[str] = field(default_factory=list)
    map_info: list[str] = field(default_factory=list)
    projection_info: list[str] = field(default_factory=list)
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def dtype(self) -> np.dtype:
        code = ENVI_DTYPES.get(self.data_type)
        if code is None:
            raise ValueError(f"unsupported ENVI data type {self.data_type}")
        return np.dtype(("<" if self.byte_order == 0 else ">") + code)

    @property
    def itemsize(self) -> int:
        return self.dtype.itemsize


def parse_header(text: str) -> EnviHeader:
    if not text.lstrip().upper().startswith("ENVI"):
        raise ValueError("not an ENVI header")
    raw: dict[str, str] = {}
    key, buf, depth = None, "", 0
    for line in text.splitlines()[1:]:
        if depth > 0 and key is not None:
            buf += " " + line.strip()
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                raw[key] = buf.strip()
                key, buf, depth = None, "", 0
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip().lower(), v.strip()
        depth = v.count("{") - v.count("}")
        if depth > 0:
            key, buf = k, v
        else:
            raw[k] = v
            depth = 0

    def lst(name: str) -> list[str]:
        v = raw.get(name, "")
        v = v.strip().lstrip("{").rstrip("}")
        return [x.strip() for x in v.split(",") if x.strip()] if v else []

    def num(name: str, default: float | None = None) -> float | None:
        v = raw.get(name)
        if v is None:
            return default
        m = re.search(r"-?\d+(\.\d*)?([eE][-+]?\d+)?", v)
        return float(m.group(0)) if m else default

    hdr = EnviHeader(
        samples=int(num("samples") or 0), lines=int(num("lines") or 0), bands=int(num("bands") or 0),
        data_type=int(num("data type") or 0), interleave=(raw.get("interleave") or "").strip().lower(),
        byte_order=int(num("byte order", 0) or 0), header_offset=int(num("header offset", 0) or 0),
        ignore_value=num("data ignore value"),
        wavelengths=[float(x) for x in lst("wavelength")] if raw.get("wavelength") else [],
        band_names=lst("band names"), map_info=lst("map info"), projection_info=lst("projection info"),
        raw=raw)
    if min(hdr.samples, hdr.lines, hdr.bands) <= 0 or hdr.interleave not in ("bil", "bsq", "bip"):
        raise ValueError("incomplete ENVI header (samples/lines/bands/interleave)")
    return hdr


class RemoteCube:
    def __init__(self, http: HttpClient, provider: str, url: str, header: EnviHeader):
        self.http, self.provider, self.url, self.h = http, provider, url, header

    async def bil_lines(self, line0: int, line1: int, bands: slice | None = None) -> np.ndarray:
        """Lines [line0, line1] (inclusive) of a BIL cube -> array (lines, bands, samples)."""
        h = self.h
        if h.interleave != "bil":
            raise ProviderError(self.provider, f"expected BIL, got {h.interleave}")
        line0, line1 = max(0, line0), min(h.lines - 1, line1)
        if line1 < line0:
            raise ProviderError(self.provider, "empty line range")
        line_bytes = h.bands * h.samples * h.itemsize
        if bands is not None and bands.start is not None and line0 == line1:
            # one line, contiguous subset of bands
            b0, b1 = bands.start, bands.stop
            off = h.header_offset + line0 * line_bytes + b0 * h.samples * h.itemsize
            data = await self.http.get_range(self.provider, self.url, off, (b1 - b0) * h.samples * h.itemsize)
            return np.frombuffer(data, dtype=h.dtype).reshape(1, b1 - b0, h.samples)
        n = line1 - line0 + 1
        data = await self.http.get_range(self.provider, self.url, h.header_offset + line0 * line_bytes,
                                         n * line_bytes)
        return np.frombuffer(data, dtype=h.dtype).reshape(n, h.bands, h.samples)

    async def bsq_rows(self, band: int, row0: int, row1: int) -> np.ndarray:
        """Rows [row0, row1] of one band of a BSQ cube -> array (rows, samples)."""
        h = self.h
        if h.interleave != "bsq":
            raise ProviderError(self.provider, f"expected BSQ, got {h.interleave}")
        row0, row1 = max(0, row0), min(h.lines - 1, row1)
        n = row1 - row0 + 1
        off = h.header_offset + ((band * h.lines + row0) * h.samples) * h.itemsize
        data = await self.http.get_range(self.provider, self.url, off, n * h.samples * h.itemsize)
        return np.frombuffer(data, dtype=h.dtype).reshape(n, h.samples)


async def open_cube(http: HttpClient, provider: str, img_url: str, hdr_url: str) -> RemoteCube:
    text = await http.get_text(provider, hdr_url, timeout=30, max_bytes=512 * 1024)
    try:
        header = parse_header(text)
    except ValueError as exc:
        raise ProviderError(provider, f"bad ENVI header {hdr_url}: {exc}") from exc
    return RemoteCube(http, provider, img_url, header)


def parse_pds3_label(text: str) -> dict[str, str]:
    """Flat KEY = VALUE map of a PDS3 label (last occurrence wins)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line and not line.strip().startswith("/*"):
            k, v = line.split("=", 1)
            out[k.strip().upper()] = v.strip().strip('"')
    return out
