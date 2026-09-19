import math
from alumina.core.calculators import (
    calculate_addition, calculate_shrinkage, calculate_absorption,
    calculate_density, calculate_loi, calculate_triaxial, calculate_umf,
)
from alumina.core.chemistry import normalize_black_profile
from alumina.data.reference import PIGMENTS, PERIODIC_DATA

def test_periodic_118():
    assert len(PERIODIC_DATA) == 118
    assert len({e["z"] for e in PERIODIC_DATA}) == 118

def test_addition():
    result = calculate_addition(100, 6)
    assert result["addition_g"] == 6
    assert result["total_g"] == 106

def test_shrinkage():
    assert math.isclose(calculate_shrinkage(100, 92), 8.0)

def test_absorption():
    assert math.isclose(calculate_absorption(100, 105), 5.0)

def test_density():
    assert math.isclose(calculate_density(150, 100), 1.5)

def test_loi():
    assert math.isclose(calculate_loi(100, 92)["loi_pct"], 8.0)

def test_triaxial_count():
    assert len(calculate_triaxial(25, 4)) == 15

def test_umf_flux_normalizes_to_one():
    result = calculate_umf("Na2O 0.25\nK2O 0.05\nCaO 0.70\nAl2O3 0.35\nSiO2 3.20")
    assert math.isclose(sum(v for _, v in result["groups"]["RO / R₂O"]), 1.0)

def test_black_profile():
    ranges = PIGMENTS["black_fe_mn_co_cr"]["ranges"]
    p = normalize_black_profile("none", 0.5, 0.1, 0.4, 1.0, ranges)
    assert math.isclose(p["FeO"] + p["MnO₂"] + p["CoO"], 1.0)
