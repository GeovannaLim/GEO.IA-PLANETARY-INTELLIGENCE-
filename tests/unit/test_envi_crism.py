import math

import numpy as np
import pytest
import respx

from app.providers.crism import MapProjection, OutsideImage, locate
from app.providers.envi import RemoteCube, parse_header, parse_pds3_label
from app.providers.http import HttpClient
from tests.conftest import run
from tests.fakes import ranged

M3_HDR = """ENVI
samples =    304
lines = 25902
bands =         85
file type = ENVI Standard
data type = 4
interleave = bil
byte order =0
data ignore value = -999.0
wavelength = {      460.9900     ,  500.9200     ,
   540.8400 }
description = {
Cumulative Processing Steps follow:
}
"""

# real header values of hrl000040ff_07_su183j_mtr3 (verified live)
SU_HDR = """ENVI
samples = 455
lines   = 751
bands   = 60
header offset = 0
data type = 4
interleave = bsq
byte order = 0
map info = {MRO Mars Equirectangular [IAU 2000] [15.00N; 0.00E], 1.0000, 1.0000, 4422632.2000, 1109935.5000, 3.6000000000e+01, 3.6000000000e+01, D_Mars_2000_IAU_IAG_custom_sphere_lat15, units=Meters}
projection info = {17, 3394839.8, 15.000000, 0.000000, 0.0, 0.0, D_Mars_2000_IAU_IAG_custom_sphere_lat15, MRO Mars Equirectangular [IAU 2000] [15.00N; 0.00E], units=Meters}
data ignore value = 6.55350000e+04
band names = {
 R770, RBR, BD530_2}
"""


def test_header_parsing():
    h = parse_header(M3_HDR)
    assert (h.samples, h.lines, h.bands, h.interleave, h.ignore_value) == (304, 25902, 85, "bil", -999.0)
    assert h.wavelengths == [460.99, 500.92, 540.84] and h.dtype == np.dtype("<f4")
    s = parse_header(SU_HDR)
    assert s.band_names == ["R770", "RBR", "BD530_2"] and len(s.map_info) >= 7
    with pytest.raises(ValueError):
        parse_header("not a header")
    with pytest.raises(ValueError):
        parse_header("ENVI\nsamples = 3\n")       # incomplete metadata


def test_crism_projection_matches_label_bounds():
    h = parse_header(SU_HDR)
    p = MapProjection.from_header(h)
    # label: MAXIMUM_LATITUDE 18.7324270, WESTERNMOST_LONGITUDE 77.2755600 (upper-left corner)
    r, c = p.pixel(18.7324270, 77.2755600)
    assert r == pytest.approx(0.0, abs=0.6) and c == pytest.approx(0.0, abs=0.6)
    row, col = locate(p, h, 18.5, 77.42)
    lat, lon = p.latlon(np.array([float(row)]), np.array([float(col)]))
    assert abs(lat[0] - 18.5) < 0.001 and abs(lon[0] - 77.42) < 0.001
    with pytest.raises(OutsideImage):
        locate(p, h, -40.0, 10.0)


def test_remote_cube_range_reads_bil_and_bsq():
    data = np.arange(4 * 3 * 5, dtype="<f4").reshape(4, 3, 5)   # lines, bands, samples
    bil = parse_header("ENVI\nsamples = 5\nlines = 4\nbands = 3\ndata type = 4\ninterleave = bil\n")
    bsq = parse_header("ENVI\nsamples = 5\nlines = 4\nbands = 3\ndata type = 4\ninterleave = bsq\n")
    bsq_data = np.transpose(data, (1, 0, 2)).copy()             # bands, lines, samples

    async def go():
        with respx.mock(assert_all_called=False) as r:
            r.get("https://pds-geosciences.wustl.edu/a.img").mock(side_effect=ranged(data.tobytes()))
            r.get("https://pds-geosciences.wustl.edu/b.img").mock(side_effect=ranged(bsq_data.tobytes()))
            http = HttpClient()
            try:
                c1 = RemoteCube(http, "t", "https://pds-geosciences.wustl.edu/a.img", bil)
                c2 = RemoteCube(http, "t", "https://pds-geosciences.wustl.edu/b.img", bsq)
                a = await c1.bil_lines(1, 2)
                b = await c1.bil_lines(3, 3, bands=slice(1, 2))
                c = await c2.bsq_rows(2, 1, 3)
            finally:
                await http.aclose()
            return a, b, c
    a, b, c = run(go())
    assert np.array_equal(a, data[1:3])
    assert np.array_equal(b[0, 0], data[3, 1])
    assert np.array_equal(c, data[1:4, 2, :])


def test_pds3_label_parsing():
    lab = parse_pds3_label('A = 1\nCH1:PIXEL_LOCATION_FILE_NAME = "M3G_V03_LOC.IMG"\n/* x = y */\n')
    assert lab["CH1:PIXEL_LOCATION_FILE_NAME"] == "M3G_V03_LOC.IMG" and "/* X" not in lab
    assert math.isfinite(1.0)
