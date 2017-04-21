# -*- coding: utf-8 -*-

"""

Chemical Similarity Enrichment
------------------------------
1. Extract all chemicals from ChEBI from BEL network

2. Get database data
    a. Get ChEBI names to ChEBI identifiers: ftp://ftp.ebi.ac.uk/pub/databases/chebi/Flat_file_tab_delimited/names.tsv.gz
    b. Get ChEBI identifiers to InChI: ftp://ftp.ebi.ac.uk/pub/databases/chebi/Flat_file_tab_delimited/chebiId_inchi.tsv
3. Map all ChEBI to InChI
4. Calculate all pairwise relationships between stuff in network and add associations for certain threshold.

Seeding by Chemical Similarity
------------------------------
- Given an InChI string, calculate all similarities to all compounds annotated in the network. Seed on node list
  of similar ones
- Calculate enrichment of similar compounds effects on certain networks (using derived NeuroMMSig algorithm)

"""
