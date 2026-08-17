"""
Candidate selection and feature matching.

This module implements the feature matching stage of the conflation
algorithm. It identifies candidate road segments using spatial filtering and
Hausdorff distance, evaluates candidates using geometric and topological
similarity metrics, assigns matching scores, and determines the most
appropriate source feature for each destination feature.
"""

import math
from qgis.core import QgsVectorLayer, QgsSpatialIndex, QgsGeometry, QgsTask
from .exceptions import ConflationCancelledException


def _assign_hausdorff_scores(candidates: list, task: QgsTask = None) -> None:
	"""Assigns Hausdorff scores to candidates based on their Hausdorff distances."""
	scores = [4, 2, 1]
	candidates.sort(key=lambda candidate: candidate["hausdorff"])
	group_rank = -1
	previous_distance = None
	for candidate in candidates:

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
		
		distance = candidate["hausdorff"]
		if previous_distance is None or not math.isclose(distance, previous_distance, rel_tol=1e-9, abs_tol=1e-12):
			group_rank += 1
			previous_distance = distance
		candidate["sh"] = scores[group_rank] if group_rank < len(scores) else 0
		del candidate["hausdorff"]

def get_candidates(geom: QgsGeometry, sindex: QgsSpatialIndex, source_layer: QgsVectorLayer,
		threshold: float, task: QgsTask = None) -> list[dict]:
	"""Finds candidate features in the source layer that are within the Hausdorff distance threshold."""
	search_buffer = geom.buffer(threshold, 10)
	candidate_ids = sindex.intersects(search_buffer.boundingBox())
	candidates = []
	for candidate_id in candidate_ids:

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
		
		candidate_feature = source_layer.getFeature(candidate_id)
		candidate_geom = candidate_feature.geometry()
		if not candidate_geom.intersects(search_buffer):
			continue
		h_distance = candidate_geom.hausdorffDistance(geom)
		if h_distance <= threshold:
			candidates.append({'candidate_id': candidate_id, 'hausdorff': h_distance})
	if candidates:
		_assign_hausdorff_scores(candidates, task=task)
		return candidates
	return []

def _score_candidate(feature_metrics: dict, candidate_metrics: dict, candidate: dict, 
		efficiency_rates: dict, std_perp_dist: float, std_mean_tri_edges: float) -> float:
	"""Calculates the score for a candidate feature based on various metrics and efficiency rates."""
	feature_orientation = feature_metrics['orientation']
	candidate_orientation = candidate_metrics['orientation']
	if candidate_orientation is None or feature_orientation is None:
		so = 0
	elif feature_orientation == candidate_orientation:
		so = 4
	elif abs(feature_orientation - candidate_orientation) in (1, 3):
		# Adjacent orientation classes differ by 1 (or 3 because of circular wrap-around)
		so = 2
	else:
		so = 0

	feature_connectivity = feature_metrics['connectivity']
	candidate_connectivity = candidate_metrics['connectivity']
	if candidate_connectivity is None or feature_connectivity is None:
		sc = 0
	elif feature_connectivity == candidate_connectivity:
		sc = 4
	elif abs(feature_connectivity - candidate_connectivity) == 1:
		sc = 2
	else:
		sc = 0

	feature_sinuosity = feature_metrics['sinuosity_level']
	candidate_sinuosity = candidate_metrics['sinuosity_level']
	if feature_sinuosity is None or candidate_sinuosity is None:
		ss = 0
	elif feature_sinuosity == candidate_sinuosity:
		ss = 2
	elif (feature_sinuosity == 'Low' and candidate_sinuosity == 'Mid') or \
		(feature_sinuosity == 'Mid' and candidate_sinuosity == 'Low') or \
		(feature_sinuosity == 'Mid' and candidate_sinuosity == 'High') or \
		(feature_sinuosity == 'High' and candidate_sinuosity == 'Mid'):
		ss = 1
	else:
		ss = 0

	feature_mean_perp_dist = feature_metrics['mean_perp_dist']
	candidate_mean_perp_dist = candidate_metrics['mean_perp_dist']
	if std_perp_dist is None:
		sp = 0
	elif abs(feature_mean_perp_dist - candidate_mean_perp_dist) <= (std_perp_dist / 2):
		sp = 2
	elif abs(feature_mean_perp_dist - candidate_mean_perp_dist) <= std_perp_dist:
		sp = 1
	else:
		sp = 0

	feature_mean_tri_edge = feature_metrics['mean_tri_edge']
	candidate_mean_tri_edge = candidate_metrics['mean_tri_edge']
	if std_mean_tri_edges is None or feature_mean_tri_edge is None or candidate_mean_tri_edge is None:
		st = 0
	elif abs(feature_mean_tri_edge - candidate_mean_tri_edge) <= (std_mean_tri_edges / 2):
		st = 2
	elif abs(feature_mean_tri_edge - candidate_mean_tri_edge) <= std_mean_tri_edges:
		st = 1
	else:
		st = 0

	score = (candidate['sh'] * efficiency_rates['H']) + (so * efficiency_rates['O']) + \
			(ss * efficiency_rates['S']) + (sp * efficiency_rates['P']) + \
			(st * efficiency_rates['T']) + (sc * efficiency_rates['C'])
	
	return score

def match_features(source_metrics: dict, destination_metrics: dict, source: QgsVectorLayer, 
	destination: QgsVectorLayer, efficiency_rates: dict, std_perp_dist: float, 
	std_mean_tri_edges: float, max_var_sinuosity: float, attributes: list, task: QgsTask = None) -> dict:
	from .metrics import _assign_sinuosity_levels
	"""Matches features from the source layer to the destination layer based
	on calculated metrics and scores."""
	_assign_sinuosity_levels(source_metrics, max_var_sinuosity)
	_assign_sinuosity_levels(destination_metrics, max_var_sinuosity)

	total_features = destination.featureCount()
	matched_features = 0

	for index, feature in enumerate(destination.getFeatures()):

		# check whether the user has requested to cancel the operation
		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")

		if task and total_features > 0:
			progress = 51 + int((index / total_features) * 49)  # Progress from 51% to 100%
			task.setProgress(progress)

		feature_id = feature.id()
		feature_metrics = destination_metrics.get(feature_id)

		if feature_metrics is None:
			continue

		candidates = feature_metrics.get("candidates", [])
		if not candidates:
			continue

		# score each candidate and find the best match
		for candidate in candidates:
			if task and task.isCanceled():
				raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
			
			candidate_metrics = source_metrics.get(candidate["candidate_id"])
			if candidate_metrics is None:
				continue
			candidate['score'] = _score_candidate(
				feature_metrics, candidate_metrics, candidate,
				efficiency_rates, std_perp_dist, std_mean_tri_edges
				)

		# select the candidate with the highest score
		best_candidate = max(candidates, key=lambda c: c['score'])
		matched_feature = source.getFeature(best_candidate['candidate_id'])

		if not matched_feature.isValid():
			continue

		# transfer attributes from the matched source feature to the destination feature
		for attr in attributes:
			feature[attr] = matched_feature[attr]
		destination.updateFeature(feature)

		matched_features += 1

	if task:
		task.setProgress(100)

	unmatched_features = total_features - matched_features
	return {
		"total_features": total_features,
		"matched_features": matched_features,
		"unmatched_features": unmatched_features,
	}