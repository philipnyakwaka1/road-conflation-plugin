"""Tests for the validation module."""

import pytest
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsField, QgsProcessingException, QgsVectorLayer

from conflate_roads.validation import add_missing_fields, validate_crs


def test_validate_crs_accepts_same_projected_crs():
    source = QgsVectorLayer("Point?crs=EPSG:3857", "source", "memory")
    destination = QgsVectorLayer("Point?crs=EPSG:3857", "destination", "memory")
    validate_crs(source, destination)


def test_validate_crs_rejects_geographic_crs():
    source = QgsVectorLayer("Point?crs=EPSG:4326", "source", "memory")
    destination = QgsVectorLayer("Point?crs=EPSG:4326", "destination", "memory")
    with pytest.raises(QgsProcessingException):
        validate_crs(source, destination)


def test_validate_crs_rejects_mismatched_crs():
    source = QgsVectorLayer("Point?crs=EPSG:3857", "source", "memory")
    destination = QgsVectorLayer("Point?crs=EPSG:32631", "destination", "memory")
    with pytest.raises(QgsProcessingException):
        validate_crs(source, destination)


def test_add_missing_fields_adds_only_missing_columns():
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "fields", "memory")
    layer.startEditing()
    layer.addAttribute(QgsField("name", QVariant.String))
    layer.updateFields()
    layer.commitChanges()

    add_missing_fields(layer, ["name", "new_field"])
    assert layer.fields().indexFromName("new_field") >= 0
    assert layer.fields().indexFromName("name") >= 0
