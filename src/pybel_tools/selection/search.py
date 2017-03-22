from pybel.constants import NAME

__all__ = [
    'search_node_names'
]


def search_node_names(graph, query):
    """Searches for nodes containing a given string

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param query: The search query
    :type query: str
    :return: An iterator over nodes whose names match the search query
    :rtype: iter
    """
    sname = query.lower()
    for node, data in graph.nodes_iter(data=True):
        if NAME not in data:
            continue
        if sname in data[NAME].lower():
            yield node
