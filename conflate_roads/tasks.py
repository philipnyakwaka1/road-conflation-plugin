from qgis.core import QgsTask
from .conflation import conflate_networks

class ConflationTask(QgsTask):
	
	def __init__(self, description, source_layer, destination_layer, fields, pattern, threshold):
		super().__init__(description, QgsTask.CanCancel)
		self.source_layer = source_layer
		self.destination_layer = destination_layer
		self.fields = fields
		self.pattern = pattern
		self.threshold = threshold

	def run(self):
		try:
			self.match_stats = conflate_networks(
				source=self.source_layer,
				destination=self.destination_layer,
				fields=self.fields,
				pattern=self.pattern,
				threshold=self.threshold,
				task=self
			)
			return True
		except Exception as e:
			self.exception = e
			return False
