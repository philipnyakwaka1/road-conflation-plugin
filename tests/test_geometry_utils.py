"""Tests for geometry_utils.py functions."""

import pytest
from qgis.core import QgsGeometry, QgsPointXY

from conflate_roads.geometry_utils import (
    calculate_sinuosity,
    compute_modified_connectivity,
    get_endpoints,
    get_orientation_class,
    get_sinuosity_level,
    intra_line_mean_perp_distance,
    point2line_distance,
)


def make_line(points):
    """Helper function to create a QgsGeometry line from a list of QgsPointXY points."""
    return QgsGeometry.fromPolylineXY(points)


def test_point2line_distance():
    """Tests the point2line_distance function with various scenarios."""
    assert point2line_distance(5, 0, 0, 0, 10, 0) == pytest.approx(0.0)
    assert point2line_distance(0, 5, -10, 0, 10, 0) == pytest.approx(5.0)


def test_intra_line_mean_perp_distance_for_straight_line_is_zero():
    geom = make_line([QgsPointXY(0, 0), QgsPointXY(10, 0), QgsPointXY(20, 0)])
    assert intra_line_mean_perp_distance(geom) == pytest.approx(0.0)


def test_intra_line_mean_perp_distance_for_bent_line_is_positive():
    geom = make_line([QgsPointXY(0, 0), QgsPointXY(5, 5), QgsPointXY(10, 0)])
    assert intra_line_mean_perp_distance(geom) > 0.0


def test_get_orientation_class_handles_cardinal_and_diagonal_cases():
    # Class 1: North-South
    assert get_orientation_class(make_line([QgsPointXY(0, 0), QgsPointXY(0, 10)])) == 1
    assert get_orientation_class(make_line([QgsPointXY(0, 10), QgsPointXY(0, 0)])) == 1

    # Class 2: Northeast-Southwest
    assert get_orientation_class(make_line([QgsPointXY(0, 0), QgsPointXY(10, 10)])) == 2
    assert get_orientation_class(make_line([QgsPointXY(10, 10), QgsPointXY(0, 0)])) == 2

    # Class 3: East-West
    assert get_orientation_class(make_line([QgsPointXY(0, 0), QgsPointXY(10, 0)])) == 3
    assert get_orientation_class(make_line([QgsPointXY(10, 0), QgsPointXY(0, 0)])) == 3

    # Class 4: Southeast-Northwest
    assert get_orientation_class(make_line([QgsPointXY(0, 10), QgsPointXY(10, 0)])) == 4
    assert get_orientation_class(make_line([QgsPointXY(10, 0), QgsPointXY(0, 10)])) == 4

def test_get_orientation_class_returns_none_for_single_point():
    geometry = make_line([QgsPointXY(0, 0)])
    assert get_orientation_class(geometry) is None

def test_get_endpoints_handles_multipart_geometry():
    geom = QgsGeometry.fromMultiPolylineXY([
        [QgsPointXY(0, 0), QgsPointXY(5, 0)],
        [QgsPointXY(10, 0), QgsPointXY(20, 0)],
    ])
    start, end = get_endpoints(geom)
    assert start == QgsPointXY(0, 0)
    assert end == QgsPointXY(20, 0)


def test_calculate_sinuosity_for_straight_line_is_approximately_one():
    geom = make_line([QgsPointXY(0, 0), QgsPointXY(10, 0), QgsPointXY(20, 0)])
    value, status = calculate_sinuosity(geom)
    assert status == "ok"
    assert value == pytest.approx(1.0)


def test_calculate_sinuosity_for_closed_loop_returns_closed_loop_status():
    geom = make_line([
        QgsPointXY(0, 0),
        QgsPointXY(1, 0),
        QgsPointXY(1, 1),
        QgsPointXY(0, 1),
        QgsPointXY(0, 0),
    ])
    value, status = calculate_sinuosity(geom)
    assert value is None
    assert status == "closed_loop"


def test_calculate_sinuosity_handles_empty_geometry():
    assert calculate_sinuosity(QgsGeometry()) == (None, "degenerate")


def test_get_sinuosity_level_classifies_levels_from_variance():
    assert get_sinuosity_level((1.0, "ok"), 0.25) == "Low"
    assert get_sinuosity_level((1.05, "ok"), 0.25) == "Mid"
    assert get_sinuosity_level((1.1, "ok"), 0.25) == "High"
    assert get_sinuosity_level((None, "closed_loop"), 0.25) == "closed_loop"


def test_compute_modified_connectivity_counts_touching_endpoints(qgis_app):
    from qgis.core import QgsFeature, QgsField, QgsSpatialIndex, QgsVectorLayer
    from PyQt5.QtCore import QVariant

    layer = QgsVectorLayer("LineString?crs=EPSG:3857", "roads", "memory")
    pr = layer.dataProvider()
    pr.addAttributes([QgsField("name", QVariant.String)])
    layer.updateFields()

    feature_a = QgsFeature(layer.fields())
    feature_a.setGeometry(make_line([QgsPointXY(0, 0), QgsPointXY(1, 0)]))
    feature_b = QgsFeature(layer.fields())
    feature_b.setGeometry(make_line([QgsPointXY(-1, 0), QgsPointXY(-0.2, 0)]))
    feature_c = QgsFeature(layer.fields())
    feature_c.setGeometry(make_line([QgsPointXY(1.2, 0), QgsPointXY(2.2, 0)]))

    layer.startEditing()
    layer.addFeature(feature_a)
    layer.addFeature(feature_b)
    layer.addFeature(feature_c)
    layer.commitChanges()

    index = QgsSpatialIndex(layer.getFeatures())
    assert compute_modified_connectivity(layer, index, feature_a, tolerance=1.0) == 2
