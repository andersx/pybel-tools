# -*- coding: utf-8 -*-

import datetime

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, Text, Binary
from sqlalchemy.orm import relationship

from pybel.manager import Base
from pybel.manager.models import NETWORK_TABLE_NAME
from .constants import reporting_log
from .security import PYBEL_WEB_USER_TABLE

PYBEL_EXPERIMENT_TABLE_NAME = 'pybel_experiment'


class Experiment(Base):
    """Represents a Candidate Mechanism Perturbation Amplitude experiment run in PyBEL Web"""
    __tablename__ = PYBEL_EXPERIMENT_TABLE_NAME

    id = Column(Integer, primary_key=True)

    created = Column(DateTime, default=datetime.datetime.utcnow, doc='The date on which this analysis was run')
    description = Column(Text, nullable=True, doc='A description of the purpose of the analysis')
    permutations = Column(Integer, doc='Number of permutations performed')
    source_name = Column(Text, doc='The name of the source file')
    source = Column(Binary, doc='The source document holding the data')
    result = Column(Binary, doc='The result python dictionary')

    network_id = Column(Integer, ForeignKey('{}.id'.format(NETWORK_TABLE_NAME)))
    network = relationship('Network', foreign_keys=[network_id])

    user_id = Column(Integer, ForeignKey('{}.id'.format(PYBEL_WEB_USER_TABLE)))
    user = relationship('User', foreign_keys=[user_id])


class Report(Base):
    """Stores information about compilation and uploading events"""
    __tablename__ = 'pybel_report'

    network_id = Column(Integer, ForeignKey('{}.id'.format(NETWORK_TABLE_NAME)), primary_key=True,
                        doc='The network that was uploaded')
    network = relationship('Network', foreign_keys=[network_id], backref='report')

    user_id = Column(Integer, ForeignKey('{}.id'.format(PYBEL_WEB_USER_TABLE)), doc='The user who uploaded the network')
    user = relationship('User', foreign_keys=[user_id], backref='reports')

    created = Column(DateTime, default=datetime.datetime.utcnow, doc='The date and time of upload')
    precompiled = Column(Boolean, doc='Was this document uploaded as a BEL script or a precompiled gpickle?')
    number_nodes = Column(Integer)
    number_edges = Column(Integer)
    number_warnings = Column(Integer)


def log_graph(graph, current_user, precompiled=False, failed=False):
    """
    
    :param pybel.BELGraph graph:
    :param current_user: 
    :param bool precompiled: 
    :param bool failed:
    """
    reporting_log.info('%s%s %s %s v%s with %d nodes, %d edges, and %d warnings', 'FAILED ' if failed else '',
                       current_user, 'uploaded' if precompiled else 'compiled', graph.name,
                       graph.version, graph.number_of_nodes(), graph.number_of_edges(), len(graph.warnings))


def add_network_reporting(manager, network, current_user, number_nodes, number_edges, number_warnings,
                          precompiled=False):
    reporting_log.info('%s %s %s v%s with %d nodes, %d edges, and %d warnings', current_user,
                       'uploaded' if precompiled else 'compiled', network.name, network.version, number_nodes,
                       number_edges, number_warnings)

    report = Report(
        network=network,
        user=current_user,
        precompiled=precompiled,
        number_nodes=number_nodes,
        number_edges=number_edges,
        number_warnings=number_warnings,
    )
    manager.session.add(report)
    manager.session.commit()
