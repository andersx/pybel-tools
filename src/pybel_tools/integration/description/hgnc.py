# -*- coding: utf-8 -*-

import logging
import time

import pandas as pd

from .node_annotator import NodeAnnotator
from ...document_utils import get_entrez_gene_data
from ...summary import get_names
from ...utils import grouper

__all__ = [
    'HGNCAnnotator',
]

log = logging.getLogger(__name__)

#: Looks up the HGNC Gene Symbol to Entrez Gene Identifier mapping from HGNC
HGNC_ENTREZ_URL = 'http://www.genenames.org/cgi-bin/download?col=gd_app_sym&col=gd_pub_eg_id&status=Approved&status_opt=2&where=&order_by=gd_app_sym_sort&format=text&limit=&hgnc_dbtag=on&submit=submit'


class HGNCAnnotator(NodeAnnotator):
    """Annotates the labels and descriptions of Genes with HGNC identifiers using a mapping provided by HGNC
    and then the Entrez Gene Service.
    """

    def __init__(self, autopopulate=False, group_size=200, sleep_time=1):
        """
        :param int group_size: The number of entrez gene id's to send per query
        :param int sleep_time: The number of seconds to sleep between queries
        """
        super(HGNCAnnotator, self).__init__('HGNC')

        # if data isn't cached
        df = pd.read_csv(HGNC_ENTREZ_URL, sep='\t')

        self.hgnc_entrez = {
            hgnc: entrez_id
            for _, hgnc, entrez_id in df[['Approved Symbol', 'Entrez Gene ID']].itertuples()
        }

        self.entrez_hgnc = {v: k for k, v in self.hgnc_entrez.items()}

        self.descriptions = {}
        self.labels = {}

        if autopopulate:
            self.populate_unconstrained(group_size, sleep_time)

    def populate(self, entrez_ids, group_size=200, sleep_time=1):
        for entrez_ids in grouper(group_size, entrez_ids):
            for entrez_id, v in get_entrez_gene_data(entrez_ids).items():

                try:
                    hgnc = self.entrez_hgnc[int(entrez_id)]

                    self.labels[hgnc] = v['description']
                    self.descriptions[hgnc] = v['summary']
                except:
                    log.warning('Missing for EGID: %s. Dat: %s', entrez_id, v)

            time.sleep(sleep_time)

    def populate_unconstrained(self, group_size=200, sleep_time=1):
        #: This variable keeps track of when the data was downloaded
        self.download_time = time.asctime()

        self.populate(
            entrez_ids=self.hgnc_entrez.values(),
            group_size=group_size,
            sleep_time=sleep_time,
        )

    def populate_constrained(self, hgnc_symbols, group_size=200, sleep_time=1):
        entrez_ids = [self.hgnc_entrez[hgnc] for hgnc in hgnc_symbols]

        self.populate(
            entrez_ids=entrez_ids,
            group_size=group_size,
            sleep_time=sleep_time,
        )

    def populate_by_graph(self, graph):
        self.populate_constrained(hgnc_symbols=get_names(graph, self.namespace))

    def get_description(self, name):
        return self.descriptions.get(name)

    def get_label(self, name):
        return self.labels.get(name)
