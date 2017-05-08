import datetime
import pickle

from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Boolean, Text, Binary
from sqlalchemy.orm import relationship

from pybel.manager import Base
from pybel.manager.models import NETWORK_TABLE_NAME
from .constants import reporting_log

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

    user_id = Column(Integer)
    name = Column(String(255))
    username = Column(String(255))

    @property
    def data(self):
        """Get unpickled data"""
        return pickle.loads(self.result)


class Report(Base):
    """Stores information about compilation and uploading events"""
    __tablename__ = 'pybel_report'

    network_id = Column(Integer, ForeignKey('{}.id'.format(NETWORK_TABLE_NAME)), primary_key=True)
    network = relationship('Network', foreign_keys=[network_id])

    user_id = Column(Integer)
    name = Column(String(255))
    username = Column(String(255))

    created = Column(DateTime, default=datetime.datetime.utcnow, doc='The date of upload')
    precompiled = Column(Boolean, doc='Was this document uploaded as a BEL script or a precompiled gpickle')
    number_nodes = Column(Integer)
    number_edges = Column(Integer)
    number_warnings = Column(Integer)


def add_network_reporting(manager, network, current_user, number_nodes, number_edges, number_warnings,
                          precompiled=False):
    report = Report(
        network=network,
        user_id=current_user.user_id,
        name=current_user.name,
        username=current_user.username,
        precompiled=precompiled,
        number_nodes=number_nodes,
        number_edges=number_edges,
        number_warnings=number_warnings,
    )
    manager.session.add(report)
    manager.session.commit()

    reporting_log.info('%s (%s) %s %s v%s with %d nodes, %d edges, and %d warnings', current_user.name,
                       current_user.username, 'uploaded' if precompiled else 'compiled', network.name, network.version,
                       number_nodes, number_edges, number_warnings)
