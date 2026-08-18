import os

import pytest
from qgis.core import QgsApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qgis_app():
    app = QgsApplication.instance()
    if app is None:
        app = QgsApplication([], False)
        app.initQgis()

    yield app

    if QgsApplication.instance() is app:
        app.exitQgis()
