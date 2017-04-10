# -*- coding: utf-8 -*-

"""

PyBEL Tools is tested on Python3 installations on Mac OS and Linux on 
`Travis CI <https://travis-ci.org/pybel/pybel-tools>`_.

.. warning:: Python2 and Windows compatibility haven't been tested

Installation
------------

Easiest
~~~~~~~
Download the latest stable code from `PyPI <https://pypi.python.org/pypi/pybel-tools>`_ with:

.. code-block:: sh

   $ python3 -m pip install pybel_tools

Get the Latest
~~~~~~~~~~~~~~~
Download the most recent code from `GitHub <https://github.com/pybel/pybel-tools>`_ with:

.. code-block:: sh

   $ python3 -m pip install git+https://github.com/pybel/pybel-tools.git@develop
"""

from . import analysis
from . import citation_utils
from . import comparison
from . import definition_utils
from . import document_utils
from . import filters
from . import generation
from . import integration
from . import ioutils
from . import mutation
from . import orthology
from . import recuration
from . import selection
from . import serialization
from . import summary
from . import utils
from . import visualization
from . import web

__version__ = '0.1.6'

__title__ = 'pybel_tools'
__description__ = 'Tools for using BEL documents in python'
__url__ = 'https://github.com/pybel/pybel-tools'

__author__ = 'Charles Tapley Hoyt'
__email__ = 'cthoyt@gmail.com'

__license__ = 'Apache License 2.0'
__copyright__ = 'Copyright (c) 2016 Charles Tapley Hoyt'
