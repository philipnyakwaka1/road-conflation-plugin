"""
Input validation and preprocessing utilities.

This module provides functions for validating algorithm inputs and preparing
layers for conflation. It includes checks such as coordinate reference system
(CRS) compatibility and projected CRS validation, as well as helper functions
for preparing output fields before attribute transfer.
"""

from qgis.core import QgsVectorLayer, QgsProcessingException, QgsField
from qgis.PyQt.QtCore import QVariant

def validate_crs(source: QgsVectorLayer, destination: QgsVectorLayer) -> None:
	"""Validates that the source and destination layers have the same projected CRS."""
	if source.crs().isGeographic() or destination.crs().isGeographic():
		raise QgsProcessingException(
			f"CRS mismatch: one or both layers do not use a projected Coordinate Reference System (CRS). "
			f"Both layers must use a projected CRS for accurate distance calculations."
		)
	if source.crs().authid() != destination.crs().authid():
		raise QgsProcessingException(
			f"CRS mismatch: source layer CRS ({source.crs().authid()}) does not match destination layer CRS ({destination.crs().authid()}). "
			f"Both layers must use the same projected CRS for accurate distance calculations."
		)

def add_missing_fields(layer: QgsVectorLayer, fields: list) -> None:
	"""Adds missing fields to the layer if they don't already exist."""
	if not layer.isEditable():
		layer.startEditing()
	for field in fields:
		if layer.fields().indexFromName(field) == -1:
			layer.addAttribute(QgsField(name=field, type=QVariant.String))
	layer.updateFields()
	layer.commitChanges()