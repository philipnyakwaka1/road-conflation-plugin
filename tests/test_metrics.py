"""Tests for the metrics module."""

import math

import pytest
from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsSpatialIndex, QgsVectorLayer
from PyQt5.QtCore import QVariant

from conflate_roads.metrics import _population_standard_deviation, calculate_feature_metrics, calculate_global_statistics


def build_layer(lines):
    layer = QgsVectorLayer("LineString?crs=EPSG:3857", "metrics", "memory")
    pr = layer.dataProvider()
    pr.addAttributes([QgsField("name", QVariant.String)])
    layer.updateFields()
    layer.startEditing()
    for index, line in enumerate(lines):
        feat = QgsFeature(layer.fields())
        feat.setAttributes([str(index)])
        feat.setGeometry(QgsGeometry.fromPolylineXY(line))
        layer.addFeature(feat)
    layer.commitChanges()
    return layer


def test_population_standard_deviation_handles_zero_count():
    assert _population_standard_deviation(0, 0, 0) is None


def test_population_standard_deviation_for_simple_values():
    assert _population_standard_deviation(2, 6, 2) == pytest.approx(math.sqrt(2.0))


def test_calculate_feature_metrics_returns_expected_metric_keys():
    layer = build_layer([
        [QgsPointXY(0, 0), QgsPointXY(10, 0), QgsPointXY(20, 0)],
        [QgsPointXY(0, 0), QgsPointXY(10, 10), QgsPointXY(20, 0)],
        [QgsPointXY(0, 0), QgsPointXY(5, 5), QgsPointXY(10, 0)],
    ])
    features = list(layer.getFeatures())
    sindex = QgsSpatialIndex(layer.getFeatures())
    mean_tri_edges = {f.id(): 1.0 for f in features}
    mean_tri_edges["count"] = 3
    mean_tri_edges["total"] = 3.0
    mean_tri_edges["total_sq"] = 9.0

    metrics, stats, has_candidates = calculate_feature_metrics(layer, sindex, mean_tri_edges)
    assert has_candidates is True
    assert set(metrics) == {f.id() for f in features}
    assert "mean_perp_dist" in metrics[features[0].id()]
    assert "sinuosity" in metrics[features[0].id()]
    assert stats["perp_count"] > 0


def test_calculate_global_statistics_handles_empty_stats_gracefully():
    assert calculate_global_statistics({}, {}) == (None, None, None)
