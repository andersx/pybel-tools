# -*- coding: utf-8 -*-

from pybel.constants import FRAUNHOFER_RESOURCES
from pybel.constants import HAS_PRODUCT, HAS_REACTANT, HAS_VARIANT, HAS_COMPONENT, TRANSCRIBED_TO, TRANSLATED_TO

IS_PRODUCT_OF = 'isProductOf'
IS_REACTANT_OF = 'isReactantOf'
IS_VARIANT_OF = 'isVariantOf'
IS_COMPONENT_OF = 'isComponentOf'
TRANSCRIBED_FROM = 'transcribedFrom'
TRANSLATED_FROM = 'translatedFrom'

INFERRED_INVERSE = {
    HAS_PRODUCT: IS_PRODUCT_OF,
    HAS_REACTANT: IS_REACTANT_OF,
    HAS_VARIANT: IS_VARIANT_OF,
    HAS_COMPONENT: IS_COMPONENT_OF,
    TRANSCRIBED_TO: TRANSCRIBED_FROM,
    TRANSLATED_TO: TRANSLATED_FROM
}

default_namespace_names = {
    'AFFX': 'affy-probeset-ids.belns',
    'CHEBI': 'chebi.belns',
    'DO': 'disease-ontology.belns',
    'DOID': 'disease-ontology-ids.belns',
    'EGID': 'entrez-gene-ids.belns',
    'GOBP': 'go-biological-process.belns',
    'GOBPID': 'go-biological-process-ids.belns',
    'GOCC': 'go-cellular-component.belns',
    'HGNC': 'hgnc-human-genes.belns',
    'MESHCS': 'mesh-cellular-structures.belns',
    'MESHD': 'mesh-diseases.belns',
    'MESHPP': 'mesh-processes.belns',
    'MGI': 'mgi-mouse-genes.belns',
    'RGD': 'rgd-rat-genes.belns',
    'SCOMP': 'selventa-named-complexes.belns',
    'SDIS': 'selventa-legacy-diseases.belns',
    'SFAM': 'selventa-protein-families.belns',
    'SP': 'swissprot.belns',
    'SPID': 'swissprot-ids.belns',
}

prfx = 'http://resource.belframework.org/belframework/20150611/namespace/'
default_namespaces = {k: FRAUNHOFER_RESOURCES + v for k, v in default_namespace_names.items()}

belief_prefix = 'http://belief.scai.fraunhofer.de/openbel/repository/namespaces/'
belief_namespaces = {
    'ADO': 'ADO.belns',
    'BRCO': 'BRCO.belns',
    'CTO': 'CTO.belns',
    'FlyBase': 'Dmel.belns',
    'NIFT': 'NIFT.belns',
    'NTN': 'Nutrition.belns',
    'PDO': 'PDO.belns',
    'PTS': 'PTS.belns',

}

belief_demo_prefix_1 = 'http://belief-demo.scai.fraunhofer.de/openbel/repository/namespaces/'
belief_demo_namespaces_1 = {
    'CHEMBL': 'chembl-names.belns',
    'CHEMBLID': 'chembl-ids.belns',
    'LMSD': 'LMSD.belns',
}

belief_demo_prefix_2 = 'http://belief-demo.scai.fraunhofer.de/BeliefDashboard/dicten/namespaces/'
belief_demo_namespaces_2 = {
    'PMIBP': 'pmibp.belns',
    'PMICHEM': 'pmichem.belns',
    'PMICOMP': 'pmicomp.belns',
    'PMIDIS': 'pmidis.belns',
    'PMIPFAM': 'pmipfam.belns',
}

DBSNP_PATTERN = 'rs[0-9]+'
EC_PATTERN = '(\d+|\-)\.((\d+)|(\-))\.(\d+|\-)(\.(n)?(\d+|\-))*'
INCHI_PATTERN = '^((InChI=)?[^J][0-9BCOHNSOPrIFla+\-\(\)\\\/,pqbtmsih]{6,})$'

default_namespace_patterns = {
    'dbSNP': DBSNP_PATTERN,
    'EC': EC_PATTERN,
    'InChI': INCHI_PATTERN
}

openbel_2013_prefix = 'http://resource.belframework.org/belframework/20131211/annotation/'
openbel_2013_annotations = {
    'Anatomy': 'anatomy.belanno',
    'Cell': 'cell.belanno',
    'CellLine': 'cell-line.belanno',
    'CellStructure': 'cell-structure.belanno',
    'Disease': 'disease.belanno',
    'MeSHAnatomy': 'mesh-anatomy.belanno',
    'MeSHDisease': 'mesh-diseases.belanno',
    'Species': 'species-taxonomy-id.belanno',
    'Gender': 'gender.belanno',
    'TextLocation': 'textlocation.belanno',
    'Confidence': 'confidence.belanno'

}
default_annotations = {k: FRAUNHOFER_RESOURCES + v for k, v in openbel_2013_annotations.items()}

abstract_url_fmt = "http://togows.dbcls.jp/entry/ncbi-pubmed/{}/abstract"
title_url_fmt = "http://togows.dbcls.jp/entry/ncbi-pubmed/{}/title"
#: SO gives short citation information
so_url_fmt = "http://togows.dbcls.jp/entry/ncbi-pubmed/{}/so"
citation_format = 'SET Citation = {{"PubMed","{}","{}"}}'
evidence_format = 'SET Evidence = "{}"'


def pubmed(name, identifier):
    return citation_format.format(name.replace('\n', ''), identifier)


CNAME = 'cname'
PUBMED = 'PubMed'
DATA_WEIGHT = 'weight'

# Resources
GENE_FAMILIES = FRAUNHOFER_RESOURCES + 'gfam_members.bel'
NAMED_COMPLEXES = 'http://resources.openbel.org/belframework/20150611/resource/named-complexes.bel'

#: Points to the env variable name for PyBEL resources
PYBEL_RESOURCES_ENV = 'PYBEL_RESOURCES_BASE'

#: Points to the env variable for ownCloud resources
OWNCLOUD_ENV = 'OWNCLOUD_BASE'

#: Points to the env variable for the biological model store repository
BMS_BASE = 'BMS_BASE'
