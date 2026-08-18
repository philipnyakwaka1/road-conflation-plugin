"""Tests for the conflate_roads plugin."""

from conflate_roads import classFactory
from conflate_roads.conflate_roads import ConflateRoads


class DummyIface:
    def __init__(self):
        self.actions = []

    def addToolBarIcon(self, action):
        self.actions.append(action)

    def addPluginToVectorMenu(self, *args):
        return None

    def removePluginVectorMenu(self, *args):
        return None

    def removeToolBarIcon(self, *args):
        return None

    def mainWindow(self):
        return None


def test_class_factory_returns_plugin_instance():
    plugin = classFactory(DummyIface())
    assert isinstance(plugin, ConflateRoads)


def test_plugin_add_action_registers_action():
    plugin = ConflateRoads(DummyIface())
    action = plugin.add_action(
        icon_path="",
        text="Test Action",
        callback=lambda: None,
        enabled_flag=True,
        add_to_menu=False,
        add_to_toolbar=False,
        status_tip="tip",
        whats_this="what",
        parent=None,
    )
    assert action.text() == "Test Action"
    assert action.isEnabled() is True
    assert len(plugin.actions) == 1

