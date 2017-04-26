# -*- coding: utf-8 -*-

import datetime
import logging
import re
import time
from collections import defaultdict

import requests

from pybel.constants import CITATION_DATE, CITATION_AUTHORS, CITATION_NAME

log = logging.getLogger(__name__)

EUTILS_URL_FMT = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id={}"


def get_citations_by_pmids(pmids, group_size=200, sleep_time=1, return_errors=False):
    """Gets the citation information for the given list of PubMed identifiers using the NCBI's eutils service

    :param pmids: an iterable of PubMed identifiers
    :type pmids: iter
    :param group_size: The number of PubMed identifiers to query at a time
    :type group_size: int
    :param sleep_time: Number of seconds to sleep between queries
    :type sleep_time: int
    :param return_errors: Should a set of erroneous PubMed identifiers be returned?
    :type return_errors: bool
    :return: A dictionary of {pmid: pmid data dictionary} or a pair of this dictionary and a set ot erroneous
            pmids if return_errors is :data:`True`
    :rtype: dict
    """
    pmids = [str(pmid).strip() for pmid in sorted(pmids)]
    log.info('querying %d PubMed identifiers', len(pmids))

    result = defaultdict(dict)
    errors = set()
    t = time.time()

    for pmidList in [','.join(pmids[i:i + group_size]) for i in range(0, len(pmids), group_size)]:
        url = EUTILS_URL_FMT.format(pmidList)
        res = requests.get(url)
        pmidsJson = res.json()

        pmid_result = pmidsJson['result']

        for pmid in pmid_result['uids']:
            p = pmid_result[pmid]
            if 'error' in p:
                log.warning("problems with following id: %s", pmid)
                errors.add(pmid)
                continue

            result[pmid][CITATION_AUTHORS] = [x['name'] for x in p['authors']] if 'authors' in p else None

            if re.search('^[12][0-9]{3} [a-zA-Z]{3} \d{1,2}$', p['pubdate']):
                result[pmid][CITATION_DATE] = datetime.datetime.strptime(p['pubdate'], '%Y %b %d').strftime('%Y-%m-%d')
            elif re.search('^[12][0-9]{3} [a-zA-Z]{3}$', p['pubdate']):
                result[pmid][CITATION_DATE] = datetime.datetime.strptime(p['pubdate'], '%Y %b').strftime('%Y-%m-01')
            elif re.search('^[12][0-9]{3}$', p['pubdate']):
                result[pmid][CITATION_DATE] = p['pubdate'] + "-01-01"
            elif re.search('^[12][0-9]{3} [a-zA-Z]{3}-[a-zA-Z]{3}$', p['pubdate']):
                result[pmid][CITATION_DATE] = datetime.datetime.strptime(p['pubdate'][:-4], '%Y %b').strftime(
                    '%Y-%m-01')
            else:
                log.info('Date with strange format: %s', p['pubdate'])

            result[pmid].update({
                'title': p['title'],
                'lastauthor': p['lastauthor'],
                CITATION_NAME: p['fulljournalname'],
                'volume': p['volume'],
                'issue': p['issue'],
                'pages': p['pages'],
                'firstauthor': p['sortfirstauthor'],
            })

        # Don't want to hit that rate limit
        time.sleep(sleep_time)

    log.info('retrieved PubMed identifiers in %s', time.time() - t)

    return result, errors if return_errors else result
