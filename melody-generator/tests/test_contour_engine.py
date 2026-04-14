from src.contour_engine import get_contour_curve


def test_contour_curve_shape_and_range():
    curve = get_contour_curve("arch", 10)
    assert len(curve) == 10
    assert all(0.0 <= x <= 1.0 for x in curve)

