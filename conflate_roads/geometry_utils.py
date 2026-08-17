"""
Geometric and topological utility functions.

This module contains low-level geometric and topological operations used
throughout the conflation algorithm. It provides reusable functions for
calculating geometric properties such as line orientation, sinuosity,
perpendicular distances, connectivity, and Delaunay-based neighbourhood
metrics.
"""

try:
	import math
	from typing import Union
	from scipy.spatial import Delaunay, QhullError
	from qgis.core import (
			QgsSpatialIndex,
			QgsGeometry,
			QgsPointXY,
			QgsRectangle,
			QgsFeature,
            QgsVectorLayer,
			QgsTask
    )
	from.exceptions import ConflationCancelledException
except ImportError as e:
    error_msg = f'This plugin requires {e.name}. Please install {e.name} in your QGIS Python environment.'

def point2line_distance(x0: float, y0: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculates distance from a point to a line using the algebraic formula."""
    dx = x1 - x2
    dy = y1 - y2
    a = dy
    b = -dx
    c = (y1 * dx) - (x1 * dy)
    
    if a == 0 and b == 0: 
        return math.hypot(x1 - x0, y1 - y0)
    return abs((a * x0) + (b * y0) + c) / math.hypot(a, b)

def _line_coordinates(geometry: QgsGeometry) -> list:
	"""Returns a list of QgsPointXY coordinates from a line geometry,
	handling both single and multi-part lines."""
	if geometry.isMultipart():
		coords = []
		for part in geometry.asMultiPolyline():
			coords.extend(part)
		return coords
	return geometry.asPolyline()

def intra_line_mean_perp_distance(geometry: QgsGeometry, task: QgsTask = None) -> float:
	"""Calculates the mean perpendicular distance of all vertices in a line to
	the straight line connecting its endpoints."""
	coords = _line_coordinates(geometry)

	if len(coords) <= 2:
		return 0.0

	x1, y1 = coords[0].x(), coords[0].y()
	x2, y2 = coords[-1].x(), coords[-1].y()

	distances = []

	for i in range(1, len(coords) - 1):

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
		
		x0, y0 = coords[i].x(), coords[i].y()

		d = point2line_distance(x0, y0, x1, y1, x2, y2)
		distances.append(d)

	return sum(distances)/ len(distances)

def get_orientation_class(geometry: QgsGeometry) -> Union[int, None]:
	"""Assigns line to one of 4 orientation classes."""
	coords = _line_coordinates(geometry)

	if len(coords) <= 1:
		return None

	dx = coords[-1].x() - coords[0].x()
	dy = coords[-1].y() - coords[0].y()
	angle = math.degrees(math.atan2(dx, dy)) % 360
    
	if (337.5 <= angle <= 360) or (0 <= angle < 22.5) or (157.5 <= angle < 202.5):
		return 1
	elif (22.5 <= angle < 67.5) or (202.5 <= angle < 247.5):
		return 2
	elif (67.5 <= angle < 112.5) or (247.5 <= angle < 292.5):
		return 3
	else:
		return 4

def get_endpoints(geometry: QgsGeometry) -> tuple[Union[QgsPointXY, None], Union[QgsPointXY, None]]:
	"""Returns the start and end points of a line geometry, handling both single 
	and multi-part lines."""
	if geometry.isMultipart():
		parts = geometry.asMultiPolyline()
		if not parts:
			return None, None
		first_part = parts[0]
		last_part = parts[-1]
		return first_part[0], last_part[-1]
	line = geometry.asPolyline()
	if not line:
		return None, None
	return line[0], line[-1]

def calculate_sinuosity(geometry: QgsGeometry) -> tuple[Union[float, None], str]:
	"""Calculates the sinuosity of a line geometry as the ratio of its actual length
	to the straight-line distance between its endpoints.Be careful with multipart geometry.
	Ensure that individual features' boundaries touch."""
	if geometry is None or geometry.isEmpty():
		return None, "degenerate"
	
	start, end = get_endpoints(geometry)
	if start is None or end is None:
		return None, "degenerate"
	
	straight_len = math.hypot(end.x() - start.x(), end.y() - start.y())
	if straight_len == 0:
		return None, 'closed_loop'
	
	return geometry.length() / straight_len, 'ok'


def get_sinuosity_level(sin_value: tuple[Union[float, None], str], max_variance: float) -> Union[str, None]:
	"""Classifies sinuosity dynamically based on the global variance threshold."""
	value, status = sin_value
	if status == 'degenerate' or max_variance is None:
		return None
	if status == 'closed_loop':
		return 'closed_loop'
	upper_bound = 1 + (max_variance / 4)
	if value < 1.0001:
		return 'Low'
	elif 1.0001 <= value < upper_bound:
		return 'Mid'
	else: 
		return 'High'

def compute_modified_connectivity(layer: QgsVectorLayer, index: QgsSpatialIndex, 
		feature: QgsFeature, tolerance: float = 1.0, task: QgsTask = None) -> Union[int, None]:
	"""Calculates the number of other lines connected to a start or end node."""

	geom = feature.geometry()
	start_pt, end_pt = get_endpoints(geom)
	if start_pt is None:
		return None
	start_geom = QgsGeometry.fromPointXY(start_pt)
	end_geom = QgsGeometry.fromPointXY(end_pt)
	start_rect = QgsRectangle(
		start_pt.x() - tolerance,
		start_pt.y() - tolerance,
		start_pt.x() + tolerance,
		start_pt.y() + tolerance
	)
	end_rect = QgsRectangle(
		end_pt.x() - tolerance,
		end_pt.y() - tolerance,
		end_pt.x() + tolerance,
		end_pt.y() + tolerance
	)
	candidate_ids = set(index.intersects(start_rect))
	candidate_ids.update(index.intersects(end_rect))
	count = 0
	for candidate_id in candidate_ids:

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")

		if candidate_id == feature.id():
			continue
		candidate = layer.getFeature(candidate_id)
		other_geom = candidate.geometry()
		if (
			other_geom.distance(start_geom) <= tolerance
			or
			other_geom.distance(end_geom) <= tolerance
		):
			count += 1
		return count

def compute_mean_triangle_edges(layer: QgsVectorLayer, task: QgsTask = None) -> dict:
	"""Builds a Delaunay triangulation from line centroids and calculates
	the mean length of neighboring edges."""

	centroids = []
	feature_ids = []

	for feature in layer.getFeatures():

		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
		
		p = feature.geometry().centroid().asPoint()
		centroids.append((p.x(), p.y()))
		feature_ids.append(feature.id())

	if len(centroids) < 3:
		# default value to avoid NameError and division by zero in subsequent calculations.
		return {"status": 'insufficient_points', "count": 0, "total": 0.0, "total_sq": 0.0}

	if task and task.isCanceled():
		raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
	
	try:
		tri = Delaunay(centroids)
		indptr, indices = tri.vertex_neighbor_vertices
	except QhullError:
		return {"status": "qhull_error", "count": 0, "total": 0.0, "total_sq": 0.0}

	mean_edges = {}
	count = 0
	total = 0
	total_sq = 0

	for i in range(len(centroids)):
		
		if task and task.isCanceled():
			raise ConflationCancelledException("Conflation process was cancelled. Changes have been rolled back.")
		
		neighbors = indices[indptr[i]:indptr[i + 1]]

		if len(neighbors) == 0:
			continue

		x1, y1 = centroids[i]
		distances = []

		for n in neighbors:
			x2, y2 = centroids[n]
			distances.append(math.hypot(x2 - x1, y2 - y1))

		mean_distance = sum(distances) / len(distances)
		mean_edges[feature_ids[i]] = mean_distance
		count += 1
		total += mean_distance
		total_sq += mean_distance ** 2

	mean_edges['count'] = count
	mean_edges['total'] = total
	mean_edges['total_sq'] = total_sq
	mean_edges['status'] = 'ok'

	return mean_edges