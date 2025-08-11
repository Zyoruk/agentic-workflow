from agentic_workflow.graph.domain.task_models import (
    Priority,
    TaskGraph,
    TaskNode,
    TaskRelationship,
    TaskStatus,
    TaskType,
)


def make_node(
    name,
    type=TaskType.CODE_GENERATION,
    status=TaskStatus.PENDING,
    priority=Priority.MEDIUM,
):
    return TaskNode(
        name=name,
        type=type,
        status=status,
        priority=priority,
    )


def make_relationship(source, target, rel_type="depends_on"):
    return TaskRelationship(
        source_id=source.id,
        target_id=target.id,
        type=rel_type,
    )


def test_tasknode_equality_and_hash():
    node1 = make_node("A")
    node2 = make_node("A")
    node2.id = node1.id
    assert node1 == node2
    assert hash(node1) == hash(node2)


def test_taskrelationship_equality_and_hash():
    node1 = make_node("A")
    node2 = make_node("B")
    rel1 = make_relationship(node1, node2)
    rel2 = make_relationship(node1, node2)
    rel2.id = rel1.id
    assert rel1 == rel2
    assert hash(rel1) == hash(rel2)


def test_add_and_get_node():
    node = make_node("A")
    graph = TaskGraph()
    graph.add_node(node)
    assert graph.get_node(node.id) == node


def test_add_and_get_relationship():
    node1 = make_node("A")
    node2 = make_node("B")
    rel = make_relationship(node1, node2)
    graph = TaskGraph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_relationship(rel)
    assert graph.get_relationship(rel.id) == rel


def test_get_dependencies_and_dependents():
    node1 = make_node("A")
    node2 = make_node("B")
    node3 = make_node("C")
    rel1 = make_relationship(node1, node2)
    rel2 = make_relationship(node2, node3)
    graph = TaskGraph()
    for n in [node1, node2, node3]:
        graph.add_node(n)
    for r in [rel1, rel2]:
        graph.add_relationship(r)
    # node2 depends on node1
    assert graph.get_dependencies(node2.id) == [node1]
    # node3 depends on node2
    assert graph.get_dependencies(node3.id) == [node2]
    # node1 has no dependencies
    assert graph.get_dependencies(node1.id) == []
    # node1 is a dependency for node2
    assert graph.get_dependents(node1.id) == [node2]
    # node2 is a dependency for node3
    assert graph.get_dependents(node2.id) == [node3]
    # node3 is not a dependency for any node
    assert graph.get_dependents(node3.id) == []


def test_cycle_detection():
    node1 = make_node("A")
    node2 = make_node("B")
    rel1 = make_relationship(node1, node2)
    rel2 = make_relationship(node2, node1)  # cycle
    graph = TaskGraph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_relationship(rel1)
    graph.add_relationship(rel2)
    assert not graph.validate_structure()


def test_no_cycle_detection():
    node1 = make_node("A")
    node2 = make_node("B")
    rel1 = make_relationship(node1, node2)
    graph = TaskGraph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_relationship(rel1)
    assert graph.validate_structure()


def test_execution_order_simple_chain():
    node1 = make_node("A")
    node2 = make_node("B")
    node3 = make_node("C")
    rel1 = make_relationship(node1, node2)
    rel2 = make_relationship(node2, node3)
    graph = TaskGraph()
    for n in [node1, node2, node3]:
        graph.add_node(n)
    for r in [rel1, rel2]:
        graph.add_relationship(r)
    order = graph.calculate_execution_order()
    # node1 must come before node2, node2 before node3
    assert order.index(node1.id) < order.index(node2.id) < order.index(node3.id)


def test_execution_order_parallel():
    node1 = make_node("A")
    node2 = make_node("B")
    node3 = make_node("C")
    rel1 = make_relationship(node1, node3)
    rel2 = make_relationship(node2, node3)
    graph = TaskGraph()
    for n in [node1, node2, node3]:
        graph.add_node(n)
    for r in [rel1, rel2]:
        graph.add_relationship(r)
    order = graph.calculate_execution_order()
    # node3 must come after both node1 and node2
    assert order.index(node1.id) < order.index(node3.id)
    assert order.index(node2.id) < order.index(node3.id)


def test_execution_order_with_no_dependencies():
    node1 = make_node("A")
    node2 = make_node("B")
    graph = TaskGraph()
    graph.add_node(node1)
    graph.add_node(node2)
    order = graph.calculate_execution_order()
    # Both nodes should be present
    assert set(order) == {node1.id, node2.id}
