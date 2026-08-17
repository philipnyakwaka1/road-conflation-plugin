"""
Feature metric computation.

This module computes the geometric and topological descriptors required for
road network matching. It derives feature-level metrics, aggregates layer
statistics, and prepares similarity measures that are subsequently used
during candidate evaluation and feature matching.
"""

import math
from typing import Union
from qgis.core import QgsVectorLayer, QgsSpatialIndex, QgsTask
from .matching import get_candidates
from .geometry_utils import (
        intra_line_mean_perp_distance,
		calculate_sinuosity, 
		get_orientation_class,
		get_sinuosity_level,
		compute_modified_connectivity,
    )

def _population_standard_deviation(sum_of_values: float, sum_of_squares: float, count: int) -> Union[float, None]:
	"""Calculates the population standard deviation."""
	if count <= 0:
		return None
	variance = (sum_of_squares / count) - (sum_of_values / count) ** 2
	variance = max(variance, 0)
	return math.sqrt(variance)

def calculate_feature_metrics(layer: QgsVectorLayer, sindex: QgsSpatialIndex, mean_tri_edges: dict, 
	threshold: float = 50.0, destination: bool = False, source_layer: QgsVectorLayer = None, 
	sindex_source: QgsSpatialIndex = None, task: QgsTask = None) -> tuple[dict, dict, bool]:
	"""Calculates the various geometric and topological metrics for each feature in the layer"""
	from .exceptions import ConflationCancelledException
	metrics_dict = {}
	stats = {
		'perp_count': 0,
		'perp': 0,
		'perp_sq': 0,
		'sinuosity_count': 0,
		'sinuosity': 0,
		'sinuosity_sq': 0
	}

	features_with_candidates = 0
	for feature in layer.getFeatures():

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
		
		geom = feature.geometry()
		candidates = None
		if destination:
			candidates = get_candidates(geom, sindex_source, source_layer, threshold, task=task)
			if not candidates:
				continue
		metrics = {
			'connectivity': compute_modified_connectivity(layer, sindex, feature, tolerance=1.0, task=task),
			'orientation': get_orientation_class(geom),
			'mean_tri_edge': mean_tri_edges.get(feature.id())
		}
		mean_perp_dist = intra_line_mean_perp_distance(geom, task=task)
		metrics['mean_perp_dist'] = mean_perp_dist
		stats['perp'] += mean_perp_dist
		stats['perp_sq'] += mean_perp_dist ** 2
		stats['perp_count'] += 1
		
		sinuosity, sinuosity_status = calculate_sinuosity(geom)
		
		if sinuosity_status == 'ok':
			metrics['sinuosity'] = (sinuosity, sinuosity_status)
			stats['sinuosity'] += sinuosity
			stats['sinuosity_sq'] += sinuosity ** 2
			stats['sinuosity_count'] += 1
		elif sinuosity_status == 'closed_loop':
			metrics['sinuosity'] = (None, sinuosity_status)
		else:
			metrics['sinuosity'] = (None, sinuosity_status)

		if destination:
			metrics['candidates'] = candidates
			features_with_candidates += 1
		metrics_dict[feature.id()] = metrics
		
	if destination and not features_with_candidates:
		return metrics_dict, stats, False
	
	var_sinuosity = (stats['sinuosity_sq'] / stats['sinuosity_count']) - (stats['sinuosity'] / stats['sinuosity_count']) ** 2 if stats['sinuosity_count'] > 0 else None
	stats['var_sinuosity'] = var_sinuosity
	stats['tri_edge'] = mean_tri_edges.get('total')
	stats['tri_edge_sq'] = mean_tri_edges.get('total_sq')
	stats['tri_edge_count'] = mean_tri_edges.get('count', 0)

	return metrics_dict, stats, True

def calculate_global_statistics(source_stats: dict, destination_stats: dict)\
	  -> tuple[Union[float, None], Union[float, None], Union[float, None]]:
    """Calculate global statistics for sinuosity variance, mean perpendicular distance, 
	and mean triangle edge length. These are used during feature matching."""

    values = [
        v for v in (
            source_stats["var_sinuosity"],
            destination_stats["var_sinuosity"],
        )
        if v is not None
    ]
    max_var_sinuosity = max(values) if values else None

    std_perp_dist = _population_standard_deviation(
        source_stats["perp"] + destination_stats["perp"],
        source_stats["perp_sq"] + destination_stats["perp_sq"],
        source_stats["perp_count"] + destination_stats["perp_count"],
    )

    std_mean_tri_edges = _population_standard_deviation(
        source_stats["tri_edge"] + destination_stats["tri_edge"],
        source_stats["tri_edge_sq"] + destination_stats["tri_edge_sq"],
        source_stats["tri_edge_count"] + destination_stats["tri_edge_count"],
    )

    return max_var_sinuosity, std_perp_dist, std_mean_tri_edges

def _assign_sinuosity_levels(metrics_map: dict, max_var_sinuosity: float) -> None:
	"""Assigns sinuosity levels to features based on their sinuosity values and the global variance."""
	for metrics in metrics_map.values():
		metrics['sinuosity_level'] = get_sinuosity_level(metrics['sinuosity'], max_var_sinuosity)