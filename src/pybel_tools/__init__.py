# -*- coding: utf-8 -*-

"""

PyBEL Tools is tested on Python3 installations on Mac OS and Linux.

.. warning:: Python2 and Windows compatibility haven't been tested

Installation
------------

Easiest
~~~~~~~

.. code-block:: sh

   $ python3 -m pip install pybel_tools

Get the Latest
~~~~~~~~~~~~~~~

.. code-block:: sh

   $ python3 -m pip install git+https://github.com/pybel/pybel-tools.git@develop
"""

from . import filters
from . import generation
from . import integration
from . import mutation
from . import selection
from . import summary
from . import visualization

__version__ = '0.1.4-dev'

__title__ = 'pybel_tools'
__description__ = 'Tools for using BEL documents in python'
__url__ = 'https://github.com/pybel/pybel-tools'

__author__ = 'Charles Tapley Hoyt'
__email__ = 'cthoyt@gmail.com'

__license__ = 'Apache License 2.0'
__copyright__ = 'Copyright (c) 2016 Charles Tapley Hoyt'
