from ..filters.node_filters import filter_nodes, build_node_name_search

__all__ = [
    'search_node_names'
]


def search_node_names(graph, query):
    """Searches for nodes containing a given string

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param query: The search query
    :type query: str or iter[str]
    :return: An iterator over nodes whose names match the search query
    :rtype: iter
    """

    return filter_nodes(graph, build_node_name_search(query))


def search_node_cnames(graph, query):
    """Searches for nodes whose canonical names contain a given string(s)

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param query: The search query
    :type query: str or iter[str]
    :return: An iterator over nodes whose names match the search query
    :rtype: iter
    """
    return filter_nodes(graph, build_node_name_search(query))
