import itertools as itt
from collections import defaultdict

from pandas import DataFrame

from pybel.constants import BIOPROCESS
from ..generation import generate_mechanism
from ..selection.induce_subgraph import get_subgraph_by_annotation
from ..selection.utils import get_nodes_by_function
from ..summary import get_annotation_values
from ..utils import tanimoto_set_similarity

__all__ = [
    'compare'
]


def compare(graph, annotation='Subgraph'):
    """Compares generated mechanisms to actual ones

    1. Generates candidate mechanisms for each bioprocess
    2. Gets subgraphs for all NeuroMMsig Subgraphs
    3. Make tanimoto similarity comparison for all sets

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to group by
    :type annotation: str
    :return: A data table comparing the canonical subgraphs to generated ones
    :rtype: pandas.DataFrame
    """

    canonical_mechanisms = {}
    for sg in get_annotation_values(graph, annotation):
        m = get_subgraph_by_annotation(graph, sg)
        # TODO filters?
        canonical_mechanisms[sg] = m

    candidate_mechanisms = {}
    for bp in get_nodes_by_function(graph, BIOPROCESS):
        m = generate_mechanism(graph, bp)
        # TODO filters?
        candidate_mechanisms[bp] = m

    canonical_nodes = {sg: set(m.nodes_iter()) for sg, m in canonical_mechanisms.items()}
    candidate_nodes = {bp: set(m.nodes_iter()) for bp, m in candidate_mechanisms.items()}

    results = defaultdict(dict)

    for candidate, canonical in itt.product(sorted(canonical_nodes), sorted(candidate_nodes)):
        candidate_nodes = canonical_nodes[candidate]
        canonical_nodes = candidate_nodes[canonical]
        tanimoto = tanimoto_set_similarity(candidate_nodes, canonical_nodes)
        results[candidate][canonical] = tanimoto

    return DataFrame(results)
