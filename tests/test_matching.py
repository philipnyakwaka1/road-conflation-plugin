"""Tests for the matching module."""

from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsSpatialIndex, QgsVectorLayer
from PyQt5.QtCore import QVariant

from conflate_roads.geometry_utils import get_sinuosity_level
from conflate_roads.matching import _assign_hausdorff_scores, get_candidates, match_features


def build_layer(lines):
    layer = QgsVectorLayer("LineString?crs=EPSG:3857", "matching", "memory")
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


def test_assign_hausdorff_scores_ranks_candidates():
    candidates = [{"hausdorff": 10.0}, {"hausdorff": 3.0}, {"hausdorff": 3.0}, {"hausdorff": 20.0}]
    _assign_hausdorff_scores(candidates)
    assert [c["sh"] for c in candidates] == [4, 4, 2, 1]


def test_get_candidates_filters_by_threshold():
    source = build_layer([
        [QgsPointXY(0, 0), QgsPointXY(10, 0)],
        [QgsPointXY(100, 100), QgsPointXY(110, 100)],
    ])
    source_features = list(source.getFeatures())
    target = QgsGeometry.fromPolylineXY([QgsPointXY(2, 0), QgsPointXY(8, 0)])
    index = QgsSpatialIndex(source.getFeatures())
    candidates = get_candidates(target, index, source, threshold=20.0)
    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == source_features[0].id()


def test_match_features_updates_destination_attributes():
    source = build_layer([
        [QgsPointXY(0, 0), QgsPointXY(10, 0)],
        [QgsPointXY(30, 0), QgsPointXY(40, 0)],
    ])
    destination = build_layer([
        [QgsPointXY(1, 0), QgsPointXY(9, 0)],
        [QgsPointXY(31, 0), QgsPointXY(39, 0)],
    ])
    source_features = list(source.getFeatures())
    destination_features = list(destination.getFeatures())
    source_metrics = {
        source_features[0].id(): {
            "orientation": 1,
            "connectivity": 0,
            "mean_perp_dist": 0.0,
            "mean_tri_edge": 10.0,
            "sinuosity": (1.0, "ok"),
            "sinuosity_level": "Low",
        },
        source_features[1].id(): {
            "orientation": 1,
            "connectivity": 0,
            "mean_perp_dist": 0.0,
            "mean_tri_edge": 10.0,
            "sinuosity": (1.0, "ok"),
            "sinuosity_level": "Low",
        },
    }
    destination_metrics = {
        destination_features[0].id(): {
            "orientation": 1,
            "connectivity": 0,
            "mean_perp_dist": 0.0,
            "mean_tri_edge": 10.0,
            "sinuosity": (1.0, "ok"),
            "sinuosity_level": "Low",
            "candidates": [{"candidate_id": source_features[0].id(), "sh": 4}],
        },
        destination_features[1].id(): {
            "orientation": 1,
            "connectivity": 0,
            "mean_perp_dist": 0.0,
            "mean_tri_edge": 10.0,
            "sinuosity": (1.0, "ok"),
            "sinuosity_level": "Low",
            "candidates": [{"candidate_id": source_features[1].id(), "sh": 4}],
        },
    }
    result = match_features(
        source_metrics=source_metrics,
        destination_metrics=destination_metrics,
        source=source,
        destination=destination,
        efficiency_rates={"H": 2.0, "O": 1.0, "S": 1.0, "P": 1.0, "T": 1.0, "C": 1.0},
        std_perp_dist=0.0,
        std_mean_tri_edges=0.0,
        max_var_sinuosity=0.1,
        attributes=["name"],
    )
    assert result["matched_features"] == 2
    assert result["unmatched_features"] == 0


def test_sinuosity_level_helper_handles_none_values():
    assert get_sinuosity_level((0.9, "ok"), 0.2) == "Low"
    assert get_sinuosity_level((None, "degenerate"), 0.2) is None
