"""
Road network conflation workflow.

This module implements the overall conflation process by coordinating the
individual stages of the algorithm, including input validation, metric
computation, candidate identification, feature matching, and attribute
transfer. It orchestrates the complete workflow while delegating individual
tasks to specialized modules.
"""
from qgis.core import QgsVectorLayer, QgsSpatialIndex, QgsProcessingException, QgsTask
from .validation import validate_crs, add_missing_fields
from .constants import get_efficiency_rates
from .metrics import calculate_feature_metrics, calculate_global_statistics
from .matching import match_features
from .geometry_utils import compute_mean_triangle_edges
from .exceptions import NoMatchesFoundException, ConflationCancelledException

def conflate_networks(source: QgsVectorLayer, destination: QgsVectorLayer, 
	fields: list, pattern: str, threshold: float, task: QgsTask = None) -> dict:
	"""
	Conflates two road networks by matching features from the source layer 
	to the destination layer based on geometric and topological metrics. 
	The algorithm transfers specified attribute fields from the source to the destination 
	for matched features. The method uses geometric and topological metrics including Hausdorff 
	distance, orientation, sinuosity, mean perpendicular distance, mean triangle edge length, 
	and modified degree of connectivity.
	Args:
		source (QgsVectorLayer): The source road network layer.
		destination (QgsVectorLayer): The destination road network layer.
		fields (list): List of attribute fields to transfer from source to destination.
		pattern (str): The efficiency rate pattern to use ('tree', 'cellular', or 'hybrid').
		threshold (float): The Hausdorff distance threshold for candidate selection.
	Raises:
		QgsProcessingException: If the CRS of the source and destination layers do not match or
		if no candidate roads are found within the specified threshold.
	Returns:
		dict: A dictionary containing the results of the conflation process.
	"""
	try:
		validate_crs(source, destination)
		
		# prepare destination layer by adding missing fields and computing efficiency rates
		add_missing_fields(destination, fields)
		efficiency_rates = get_efficiency_rates(pattern)

		if task:
			task.setProgress(5)

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled.")

		# create spatial indexes for both layers
		sindex_source = QgsSpatialIndex(source.getFeatures())

		if task:
			task.setProgress(10)
		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled.")
		
		sindex_destination = QgsSpatialIndex(destination.getFeatures())

		if task:
			task.setProgress(15)

		# pre-compute mean triangle edges for both layers. If Delaunay fails we simply score without this metric. 
		source_triangle_edges = compute_mean_triangle_edges(source, task=task)

		if task:
			task.setProgress(20)

		destination_triangle_edges = compute_mean_triangle_edges(destination, task=task)

		if task:
			task.setProgress(25)

		# compute metrics for both layers. If no candidates are found for any feature in the destination layer, raise an exception.
		source_metrics, source_stats, _ = calculate_feature_metrics(
			layer=source,
			sindex=sindex_source,
			mean_tri_edges=source_triangle_edges,
			threshold=threshold,
			task=task
		)

		if task:
			task.setProgress(35)

		destination_metrics, destination_stats, has_candidates = (
			calculate_feature_metrics(
				layer=destination,
				sindex=sindex_destination,
				mean_tri_edges=destination_triangle_edges,
				threshold=threshold,
				destination=True,
				source_layer=source,
				sindex_source=sindex_source,
				task=task
			)
		)
		if task:
			task.setProgress(45)

	except ConflationCancelledException as e:
		raise
	except Exception as e:
		raise QgsProcessingException(str(e))
	
	if not has_candidates:
		raise NoMatchesFoundException(
			f"No candidate roads were found within the specified threshold "
			f"({threshold} map units)."
		)
	
	# calculate global statistics
	max_var_sinuosity, std_perp_dist, std_mean_tri_edges = calculate_global_statistics(
		source_stats, destination_stats)

	if task:
		task.setProgress(50)

    # perform matching
	started_editing = False

	try:
		if not destination.isEditable():
			destination.startEditing()
			started_editing = True

		match_stats = match_features(
			source_metrics=source_metrics,
			destination_metrics=destination_metrics,
			source=source,
			destination=destination,
			efficiency_rates=efficiency_rates,
			std_perp_dist=std_perp_dist,
			std_mean_tri_edges=std_mean_tri_edges,
			max_var_sinuosity=max_var_sinuosity,
			attributes=fields,
			task=task
		)

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")

		if started_editing:
			destination.commitChanges()

	except ConflationCancelledException as e:
		if started_editing and destination.isEditable():
			destination.rollBack()
		raise
	except Exception as e:
		if started_editing and destination.isEditable():
			destination.rollBack()
		raise QgsProcessingException(f"An error occurred during the conflation process: {str(e)}. Changes have been rolled back.")
	
	return match_stats
