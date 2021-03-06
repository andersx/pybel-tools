# -*- coding: utf-8 -*-

"""This module assists in running complex workflows on BEL graphs"""

from __future__ import print_function

import logging
import pickle
from functools import wraps

__all__ = [
    'PipelineBuilder',
    'in_place_mutator',
    'uni_in_place_mutator',
    'uni_mutator',
    'mutator'
]

log = logging.getLogger(__name__)


class PipelineBuilder:
    """Builds and runs analytical pipelines on BEL graphs"""

    def __init__(self, universe=None):
        """
        :param universe: The entire set of known knowledge to draw from
        :type universe: pybel.BELGraph 
        """
        self.universe = universe
        self.protocol = []

    def wrap_universe_protocol(self, f):
        """Takes a function that needs a universe graph as the first argument and returns a wrapped one"""

        @wraps(f)
        def wrapper(graph, argument):
            if self.universe is None:
                raise ValueError('No universe is set in PipelineBuilder')

            return f(self.universe, graph, argument)

        return wrapper

    @staticmethod
    def wrap_in_place(f):
        """Takes a function that doesn't return the graph and returns the graph"""

        @wraps(f)
        def wrapper(graph, *attrs, **kwargs):
            f(graph, *attrs, **kwargs)
            return graph

        return wrapper

    def add_universe_protocol(self, f, *attrs, **kwargs):
        """Adds a function that takes the universe as its first argument to the protocol"""
        self._add_protocol(True, False, self.wrap_universe_protocol(f), *attrs, **kwargs)

    def add_mutation_protocol(self, f, *attrs, **kwargs):
        """Adds a function that mutates a graph to the protocol"""
        self._add_protocol(False, False, f, *attrs, **kwargs)

    def add_universe_protocol_inplace(self, f, *attrs, **kwargs):
        """Adds a function that takes the universe as its first argument to the protocol"""
        self._add_protocol(True, True, self.wrap_in_place(self.wrap_universe_protocol(f)), *attrs, **kwargs)

    def add_mutation_protocol_inplace(self, f, *attrs, **kwargs):
        """Adds a function that mutates a graph to the protocol"""
        self._add_protocol(False, True, self.wrap_in_place(f), *attrs, **kwargs)

    def _add_protocol(self, universe, wrapped, f, *attrs, **kwargs):
        self.protocol.append((universe, wrapped, f, attrs, kwargs))

    def add_protocol(self, f, *attrs, **kwargs):
        if not hasattr(f, 'wrap_universe'):
            raise ValueError('{} is not wrapped with a pipeline decorator'.format(f.__name__))

        if f.wrap_universe:
            if f.wrap_in_place:
                self.add_universe_protocol_inplace(f, *attrs, **kwargs)
            else:
                self.add_universe_protocol(f, *attrs, **kwargs)
        else:
            if f.wrap_in_place:
                self.add_mutation_protocol_inplace(f, *attrs, **kwargs)
            else:
                self.add_mutation_protocol(f, *attrs, **kwargs)

    def run_protocol(self, graph, universe=None):
        """Runs the contained protocol on a seed graph
        
        :param graph: The seed BEL graph
        :type graph: pybel.BELGraph 
        """
        if universe is not None:
            self.universe = universe

        result = graph
        for _, _, f, attrs, kwargs in self.protocol:
            result = f(result, *attrs, **kwargs)
        return result

    def print_summary(self, file=None):
        """Prints as summary of the protocol"""
        for universe, wrapped, func, attrs, kwargs in self.protocol:
            print(universe, wrapped, func, attrs, kwargs, file=file)

    def to_pickle(self, file):
        log.info('Dumping protocol')
        pickle.dump(self.protocol, file)

    @staticmethod
    def from_pickle(file):
        protocol = pickle.load(file)
        pipeline_builder = PipelineBuilder()
        pipeline_builder.protocol = protocol
        return pipeline_builder


universe_cache = {}
in_place_cache = {}


def mutator_decorator_builder(wrap_universe, wrap_in_place):
    """Builds a decorator function to tag mutator functions"""

    def decorator(f):
        """A decorator that tags mutator functions"""

        @wraps(f)
        def wrapper(*attrs, **kwargs):
            return f(*attrs, **kwargs)

        wrapper.wrap_universe = wrap_universe
        wrapper.wrap_in_place = wrap_in_place

        if wrap_universe:
            universe_cache[wrapper.__name__] = wrapper

        if wrap_in_place:
            in_place_cache[wrapper.__name__] = wrapper

        return wrapper

    return decorator


#: A function decorator to inform the Pipeline how to handle a function
in_place_mutator = mutator_decorator_builder(wrap_universe=False, wrap_in_place=True)
#: A function decorator to inform the Pipeline how to handle a function
uni_in_place_mutator = mutator_decorator_builder(wrap_universe=True, wrap_in_place=True)
#: A function decorator to inform the Pipeline how to handle a function
uni_mutator = mutator_decorator_builder(wrap_universe=True, wrap_in_place=False)
#: A function decorator to inform the Pipeline how to handle a function
mutator = mutator_decorator_builder(wrap_universe=False, wrap_in_place=False)
