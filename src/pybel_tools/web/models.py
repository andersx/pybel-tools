# -*- coding: utf-8 -*-

import datetime

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, Text, Binary
from sqlalchemy import func
from sqlalchemy.orm import relationship

from pybel.manager import Base
from pybel.manager.models import NETWORK_TABLE_NAME, Network
from .constants import reporting_log
from .security import PYBEL_WEB_USER_TABLE

PYBEL_EXPERIMENT_TABLE_NAME = 'pybel_experiment'
PYBEL_REPORT_TABLE_NAME = 'pybel_report'


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
    __tablename__ = PYBEL_REPORT_TABLE_NAME

    network_id = Column(Integer, ForeignKey('{}.id'.format(NETWORK_TABLE_NAME)), primary_key=True,
                        doc='The network that was uploaded')
    network = relationship('Network', foreign_keys=[network_id], backref='report')

    user_id = Column(Integer, ForeignKey('{}.id'.format(PYBEL_WEB_USER_TABLE)), doc='The user who uploaded the network')
    user = relationship('User', foreign_keys=[user_id], backref='reports')

    created = Column(DateTime, default=datetime.datetime.utcnow, doc='The date and time of upload')
    public = Column(Boolean, nullable=False, default=False, doc='Should the network be viewable to the public?')
    precompiled = Column(Boolean, doc='Was this document uploaded as a BEL script or a precompiled gpickle?')
    number_nodes = Column(Integer)
    number_edges = Column(Integer)
    number_warnings = Column(Integer)

    def __repr__(self):
        return '<Report on {}>'.format(self.network)

    def __str__(self):
        return repr(self)


def log_graph(graph, current_user, preparsed=False, failed=False):
    """
    
    :param pybel.BELGraph graph:
    :param current_user: 
    :param bool preparsed: 
    :param bool failed:
    """
    reporting_log.info('%s%s %s %s v%s with %d nodes, %d edges, and %d warnings', 'FAILED ' if failed else '',
                       current_user, 'uploaded' if preparsed else 'compiled', graph.name,
                       graph.version, graph.number_of_nodes(), graph.number_of_edges(), len(graph.warnings))


def add_network_reporting(manager, network, current_user, number_nodes, number_edges, number_warnings,
                          preparsed=False, public=True):
    reporting_log.info('%s %s %s v%s with %d nodes, %d edges, and %d warnings', current_user,
                       'uploaded' if preparsed else 'compiled', network.name, network.version, number_nodes,
                       number_edges, number_warnings)

    report = Report(
        network=network,
        user=current_user,
        precompiled=preparsed,
        number_nodes=number_nodes,
        number_edges=number_edges,
        number_warnings=number_warnings,
        public=public,
    )
    manager.session.add(report)
    manager.session.commit()


def get_recent_reports(manager, weeks=2):
    """Gets reports from the last two weeks

    :param pybel.manager.CacheManager manager: A cache manager
    :param int weeks: The number of weeks to look backwards (builds :class:`datetime.timedelta`)
    :return: An iterable of the string that should be reported
    :rtype: iter[str]
    """
    now = datetime.datetime.utcnow()
    delta = datetime.timedelta(weeks=weeks)
    q = manager.session.query(Report).filter(Report.created - now < delta).join(Network).group_by(Network.name)
    q1 = q.having(func.min(Report.created)).order_by(Network.name.asc()).all()
    q2 = q.having(func.max(Report.created)).order_by(Network.name.asc()).all()

    q3 = manager.session.query(Report, func.count(Report.network)). \
        filter(Report.created - now < delta). \
        join(Network).group_by(Network.name). \
        order_by(Network.name.asc()).all()

    for a, b, (_, count) in zip(q1, q2, q3):
        yield a.network.name

        if a.network.version == b.network.version:
            yield '\tUploaded only once'
            yield '\tNodes: {}'.format(a.number_nodes)
            yield '\tEdges: {}'.format(a.number_edges)
            yield '\tWarnings: {}'.format(a.number_warnings)
        else:
            yield '\tUploads: {}'.format(count)
            yield '\tVersion: {} -> {}'.format(a.network.version, b.network.version)
            yield '\tNodes: {} {:+d} {}'.format(a.number_nodes, b.number_nodes - a.number_nodes, b.number_nodes)
            yield '\tEdges: {} {:+d} {}'.format(a.number_edges, b.number_edges - a.number_edges, b.number_edges)
            yield '\tWarnings: {} {:+d} {}'.format(a.number_warnings, b.number_warnings - a.number_warnings,
                                                   b.number_warnings)
        yield ''
