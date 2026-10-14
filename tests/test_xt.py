import numpy as np

from pipeline.xt_model import NX, NY, zone


def test_zone_corners():
    assert zone(np.array([0.0]), np.array([0.0]))[0] == 0
    assert zone(np.array([120.0]), np.array([80.0]))[0] == NX * NY - 1


def test_zone_is_in_range():
    xs = np.random.uniform(0, 120, 1000)
    ys = np.random.uniform(0, 80, 1000)
    z = zone(xs, ys)
    assert z.min() >= 0 and z.max() < NX * NY
