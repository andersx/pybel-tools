# -*- coding: utf-8 -*-

"""This module assists in running complex workflows on BEL graphs"""

from pybel import BELGraph
from .summary.export import info_list
from functools import wraps
OPERATION_PROVENANCE = 'operation_provenance'


# TODO make more strict for non-in place operations so it's possible to perform a functional "reduce"
def transform(graph, *transformations):
    """Applies a series of transformations to a graph

    This function mixes the ability to perform in-place and copying operations, so it's
    a good idea to assume the original graph isn't stable after applying this function.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A transformed BEL graph
    :rtype: pybel.BELGraph
    """

    current_graph = graph

    for transformation in transformations:
        result = transformation(current_graph)
        if isinstance(result, BELGraph):
            current_graph = result

    return current_graph


def add_operation(graph, operation_info):
    """Adds annotations to the graph about what transformations were applied

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param operation_info: A dictionary containing information about the function that was applied
    :type operation_info: dict
    """
    if OPERATION_PROVENANCE not in graph.graph:
        graph.graph[OPERATION_PROVENANCE] = []
    graph.graph[OPERATION_PROVENANCE].append(operation_info)


def summarize_operation_list(graph, graph_function):
    """Applies an operation to the graph then returns a list with the information about the change in the
    graph's properties.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param graph_function: A mutation function that takes (graph, ) -> None
    :type graph_function: lambda
    :return: A list of the change in each aspect of the graph
    :rtype: list
    """
    pre_list = info_list(graph)
    graph_function(graph)
    post_list = info_list(graph)

    result = [pre_list[0]]

    for (k, before), (_, after) in zip(pre_list, post_list):
        result.append((k, after - before))

    return result


class Pipeline:
    """Builds and runs analytical pipelines on BEL graphs"""

    def __init__(self, universe):
        """
        :param universe: The entire set of known knowledge to draw from
        :type universe: pybel.BELGraph 
        """
        self.universe = universe
        self.protocol = []

    def wrap_universe_protocol(self, func):
        """Takes a function that needs a universe graph as the first argument and returns a wrapped one"""

        def universe_protocol(graph, argument):
            """Applys the function with the contained universe graph"""
            return func(self.universe, graph, argument)

        universe_protocol.__doc__ = func.__doc__

        return universe_protocol

    def wrap_in_place(self, func):
        def wrapped(graph, *attrs, **kwargs):
            func(graph, *attrs, **kwargs)
            return graph

        return wrapped

    def add_universe_protocol(self, func, *attrs, **kwargs):
        """Adds a function that takes the universe as its first argument to the protocol"""
        self._add_protocol(True, False, self.wrap_universe_protocol(func), *attrs, **kwargs)

    def add_mutation_protocol(self, func, *attrs, **kwargs):
        """Adds a function that mutates a graph to the protocol"""
        self._add_protocol(False, False, func, *attrs, **kwargs)

    def add_universe_protocol_inplace(self, func, *attrs, **kwargs):
        """Adds a function that takes the universe as its first argument to the protocol"""
        self._add_protocol(True, True, self.wrap_in_place(self.wrap_universe_protocol(func)), *attrs, **kwargs)

    def add_mutation_protocol_inplace(self, func, *attrs, **kwargs):
        """Adds a function that mutates a graph to the protocol"""
        self._add_protocol(False, True, self.wrap_in_place(func), *attrs, **kwargs)

    def _add_protocol(self, wrapped, func, *attrs, **kwargs):
        self.protocol.append((wrapped, func, attrs, kwargs))

    def run_protocol(self, graph):
        """Runs the contained protocol on a seed graph
        
        :param graph: The seed BEL graph
        :type graph: pybel.BELGraph 
        """
        result = graph
        for _, _, func, attrs, kwargs in self.protocol:
            result = func(result, *attrs, **kwargs)
        return result

    def print_summary(self, file=None):
        """Prints as summary of the protocol"""
        for wrapped, func, attrs, kwargs in self.protocol:
            print(wrapped, func, attrs, kwargs, file=file)

    @staticmethod
    def runnable(wrap_universe, wrap_in_place):
        def decorator(func):
            @wraps(func)
            def wrapper(*attrs, **kwargs):
                func(*attrs, **kwargs)

            wrapper.wrap_universe = wrap_universe
            wrapper.wrap_in_place = wrap_in_place
            return wrapper

        return decorator


#: A function decorator to inform the Pipeline how to handle a function
in_place_mutator = Pipeline.runnable(wrap_universe=False, wrap_in_place=True)
uni_in_place_mutator = Pipeline.runnable(wrap_universe=True, wrap_in_place=True)
uni_mutator = Pipeline.runnable(wrap_universe=True, wrap_in_place=False)
mutator = Pipeline.runnable(wrap_universe=False, wrap_in_place=False)