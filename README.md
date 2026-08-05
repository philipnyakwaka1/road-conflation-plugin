# road-conflation-plugin
An open-source QGIS plugin for automated road network conflation. It transfers attributes from a reference road dataset to a target dataset by identifying the most likely corresponding road segments using a multi-metric matching algorithm.

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
		None
	"""


Congratulations! You just built a plugin for QGIS!


Your plugin ConflateRoads was created in:
  C:/github/road-conflation-plugin\conflate_roads 
Your QGIS plugin directory is located at:
  C:/Users/omina/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins 
What's Next
If resources.py is not present in your plugin directory, compile the resources file using pyrcc5 (simply use pb_tool or make if you have automake) 
Optionally, test the generated sources using make test (or run tests from your IDE) 
Copy the entire directory containing your new plugin to the QGIS plugin directory (see Notes below) 
Test the plugin by enabling it in the QGIS plugin manager 
Customize it by editing the implementation file conflate_roads.py 
Create your own custom icon, replacing the default icon.png 
Modify your user interface by opening conflate_roads_dialog_base.ui in Qt Designer 
Notes: 
You can use pb_tool to compile, deploy, and manage your plugin. Tweak the pb_tool.cfg file included with your plugin as you add files. Install pb_tool using pip or easy_install. See http://loc8.cc/pb_tool for more information. 
You can also use the Makefile to compile and deploy when you make changes. This requires GNU make (gmake). The Makefile is ready to use, however you will have to edit it to add addional Python source files, dialogs, and translations. 
For information on writing PyQGIS code, see http://loc8.cc/pyqgis_resources for a list of resources. 
©2011-2019 GeoApt LLC - geoapt.com 

Step 1: Created symbolic lynk
mklink /D "C:\Users\omina\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\conflate_roads" "C:\github\road-conflation-plugin\conflate_roads"

Step2: Create resources.qrc and generate resources.py, then import resources in plugin main script

