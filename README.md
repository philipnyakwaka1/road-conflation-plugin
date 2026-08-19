
# Conflate Roads

Conflate Roads is a QGIS plugin for identifying corresponding road features between two polyline datasets and transferring selected attributes from a source road layer to a destination road layer. It is designed for road-network conflation, attribute completion, and enrichment of incomplete or missing road attributes.

## Requirements

- QGIS 3.36 or later. The plugin has been tested on QGIS 3.36 and QGIS 3.44.13 LTR.
- Two polyline road layers in the same projected, metric CRS. The plugin
  validates that the CRS definitions match before processing.
- Python package `scipy`, which is not guaranteed to be included in a QGIS
  installation. The plugin uses `scipy.spatial.Delaunay` to calculate the
  mean length of neighbouring triangle edges.

The plugin itself uses QGIS/PyQt APIs, Python’s standard library, and SciPy.
It does not require a separate database, web service, or network connection.

### Installing SciPy on Windows

First check whether SciPy is already available in the QGIS runtime. In QGIS,
open **Plugins > Python Console** and run:

```python
try:
	import scipy
	print("SciPy is available:", scipy.__version__)
except ImportError:
	print("SciPy is not available in this QGIS environment.")
```

Only install SciPy if the check reports that it is unavailable. Use the QGIS
Python environment, rather than a separate system Python installation:

```python
import sys
print(sys.executable)
```

Use the displayed interpreter with `pip` in an OSGeo4W Shell or PowerShell
opened with the same QGIS environment:

```powershell
& "C:\OSGeo4W\bin\python-qgis-ltr.bat" -m pip install scipy
```

This is the QGIS Long Term Release interpreter used by this project. If your
OSGeo4W installation is in a different location, use its equivalent
`python-qgis-ltr.bat` path. Restart QGIS after installation. Do not install
SciPy into an unrelated system Python environment, because QGIS will not load
packages from it.

### Example data

The `example_data` directory contains sample source and destination road
datasets that can be used to test the Conflate Roads plugin. Load both layers
into QGIS and select them as the source and destination layers in the plugin.
The sample GeoPackages use a projected CRS suitable for metric distance
calculations; confirm the CRS and metre-based units in QGIS before running the
match.

## Methodology

The plugin follows the geometric-integration approach described by Hacar and
Gökgöz (2021). For each destination feature, a spatial search first identifies
source candidates whose Hausdorff distance is within the user-defined search
buffer. Each candidate is then evaluated with six similarity measures:

1. Hausdorff distance (`H`), measuring the maximum of the minimum distances between points on the two candidate geometries.
2. Orientation (`O`), comparing the features’ four directional classes.
3. Sinuosity (`S`), comparing the ratio of line length to endpoint distance.
4. Mean perpendicular distance (`P`), comparing the average perpendicular deviation of each feature from the straight line connecting its endpoints.
5. Mean triangle-edge length (`T`), measuring the mean length of Delaunay-triangulation edges connecting neighbouring feature centroids.
6. Modified degree of connectivity (`C`), comparing the number of connected
	road features at each endpoint.

The raw scores are weighted with efficiency rates for the selected road
pattern, following Hacar and Gökgöz (2019). The total score is:

```text
S = EH*H + EO*O + ES*S + EP*P + ET*T + EC*C
```

The source candidate with the highest total score is selected. The checked
source attributes are then copied to the corresponding destination feature;
missing destination fields are added automatically. The built-in efficiency
rates are:

| Pattern | EH | EO | ES | EP | ET | EC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 1.64067 | 1.32845 | 1.01742 | 1.00000 | 1.00000 | 1.02644 |
| Tree | 2.00000 | 1.28409 | 1.03978 | 1.00000 | 1.03356 | 1.08765 |
| Cellular | 2.00000 | 1.16961 | 1.00000 | 1.00000 | 1.11875 | 1.17006 |

Sinuosity and mean perpendicular distance have a maximum raw score of 2 each;
the other measures have a maximum raw score of 4. This prevents the two
closely related line-shape measures from dominating the combined score.

## Using the plugin

1. Add both road layers to QGIS and confirm that they use the same projected
	CRS with metre-based units. Select **Vector > Conflate Roads > Road Network
	Conflation**.
2. Select the **Source Layer**. This is the reference layer whose attributes
	will be transferred. The layer must be a vector layer.
3. Select the **Destination Layer**. This is the layer whose geometries are
	matched and whose attributes are updated. It must also be a vector layer.
4. Select one or more **Attributes to Transfer**. The list is populated from
	the source layer. The selected field names must be usable in the destination
	data; missing destination fields are created by the plugin.
5. Select a **Road Pattern**: `Hybrid`, `Tree`, or `Cellular`. There is no
	default selection because this choice controls the efficiency-rate weights.
	`Hybrid` is a reasonable starting point for a mixed road network.
6. Set **Search Buffer (m)**, the maximum Hausdorff distance used to identify
	candidate source roads. The default is `50` metres and the value must be
	positive. Increase it when the datasets are less closely aligned, but expect
	more candidates and longer processing times.
7. Choose an output path with **Browse** or enter one directly. The supported
	formats are GeoPackage (`.gpkg`), Shapefile (`.shp`), and GeoJSON
	(`.geojson`). The output file is overwritten if it already exists.
8. Click **OK**. A cancellable progress dialog is shown. On completion, QGIS
	reports total, matched, and unmatched destination features and offers to add
	the output layer to the current project.

### Preparing road data

Optional affine preprocessing can improve spatial overlap when corresponding
features are displaced or differently aligned. Apply that preprocessing before
running the plugin. Split long road segments at existing vertices when the
other dataset represents the same road as several shorter segments: the
Hausdorff threshold is evaluated for individual candidate features and may
otherwise reject valid matches.

Multipart line features deserve special attention. Sinuosity assumes a
continuous LineString or MultiLineString; multipart segments should touch in
sequence. Disconnected parts can produce undesirable sinuosity values and
reduce match quality. Features with no candidate within the threshold remain
unmatched.

## Running the tests

The tests are in `tests/` and use `pytest`. `pytest` is a development
dependency and may not be included in the QGIS Python installation. Install it
alongside SciPy in the QGIS environment:

```powershell
& "C:\OSGeo4W\bin\python-qgis-ltr.bat" -m pip install pytest
```

From the repository root, activate the environment that can import `qgis` and
run:

```powershell
& "C:\OSGeo4W\bin\python-qgis-ltr.bat" -m pytest
```

The test fixture starts QGIS in offscreen mode. If `qgis.core` cannot be
imported, run the command from an OSGeo4W/QGIS shell or configure
`PYTHONPATH` and the QGIS environment to match your installation. A focused
test run is also possible:

```powershell
& "C:\OSGeo4W\bin\python-qgis-ltr.bat" -m pytest tests/test_matching.py
```

The same interpreter can be used to confirm the runtime dependencies from an
OSGeo4W Shell or PowerShell:

```powershell
& "C:\OSGeo4W\bin\python-qgis-ltr.bat" -c "import qgis, scipy, pytest; print('QGIS, SciPy, and pytest are available')"
```

## Installation and packaging

For development, copy the `conflate_roads` directory into the active QGIS
profile’s `python/plugins` directory, then enable **Conflate Roads** in
**Plugins > Manage and Install Plugins**. For distribution, use the packaged
`conflate_roads.zip` archive from this repository or create a fresh archive
containing the `conflate_roads/` directory at its root. In QGIS, choose
**Plugins > Manage and Install Plugins > Install from ZIP**.

The archive must not contain `.git`, `__pycache__`, test data, or generated
development files. The plugin is distributed under the GNU General Public
License, version 2 or later; see [LICENSE](LICENSE).

## References

- Hacar, M., & Gökgöz, T. (2019). A New, Score-Based Multi-Stage Matching Approach for Road Network Conflation in Different Road Patterns. ISPRS International Journal of Geo-Information, 8(2), 81. https://doi.org/10.3390/ijgi8020081

- Hacar, M., & Gökgöz, T. (2021). A new approach for matching road lines using efficiency rates of similarity measures. International Journal of Engineering and Geosciences, 6(3), 146–156. https://doi.org/10.26833/ijeg.791324


## Project links

- [Issue tracker](https://github.com/philipnyakwaka1/road-conflation-plugin/issues)