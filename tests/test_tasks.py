"""Tests for the tasks module."""

from conflate_roads.tasks import ConflationTask


def test_conflation_task_initializes_fields():
    task = ConflationTask(
        description="Test task",
        source_layer=None,
        destination_layer=None,
        fields=["name"],
        pattern="tree",
        threshold=10.0,
    )
    assert task.description() == "Test task"
    assert task.fields == ["name"]
    assert task.pattern == "tree"
    assert task.threshold == 10.0
