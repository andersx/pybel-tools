import datetime

from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Boolean
from sqlalchemy.orm import relationship

from pybel.manager import Base
from pybel.manager.models import NETWORK_TABLE_NAME
from .constants import reporting_log


class NetworkUser(Base):
    """Stores information about compilation and uploading events"""
    __tablename__ = 'pybel_network_user'

    network_id = Column(Integer, ForeignKey('{}.id'.format(NETWORK_TABLE_NAME)), primary_key=True)
    network = relationship('Network', foreign_keys=[network_id])

    created = Column(DateTime, default=datetime.datetime.utcnow, doc='The date on which this analysis was run')

    name = Column(String(255))
    username = Column(String(255))

    precompiled = Column(Boolean, doc='Was this document uploaded as a BEL script or a precompiled gpickle')
    number_nodes = Column(Integer)
    number_edges = Column(Integer)
    number_warnings = Column(Integer)


def add_network_reporting(manager, network, name, username, number_nodes, number_edges, number_warnings,
                          precompiled=False):
    network_user = NetworkUser(
        network=network,
        name=name,
        username=username,
        precompiled=precompiled,
        number_nodes=number_nodes,
        number_edges=number_edges,
        number_warnings=number_warnings,
    )
    manager.session.add(network_user)
    manager.session.commit()

    reporting_log.info('%s (%s) %s %s v%s with %d nodes, %d edges, and %d warnings', name, username,
                       'uploaded' if precompiled else 'compiled', network.name, network.version, number_nodes,
                       number_edges, number_warnings)
