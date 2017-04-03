PyBEL Tools
===========

Installation
------------
PyBEL Tools can be installed easily from `PyPI <https://pypi.python.org/pypi/pybel_tools>`_ with the following code in
your favorite terminal:

.. code-block:: sh

    python3 -m pip install pybel_tools

or from the latest code on GitHub with:

.. code-block:: sh

    python3 -m pip install git+https://github.com/pybel/pybel-tools.git@develop

Documentation
-------------
Documentation at http://pybel-tools.readthedocs.io/en/latest/.

Setting up with Docker
----------------------
- http://phusion.github.io/baseimage-docker/
- https://penandpants.com/2014/03/09/docker-via-homebrew/

Running the PyBEL Tool's service
----------------------
Running the PyBEL Tools Flask application allows you to interact with your networks and apply filters/algorithms.
.. code-block:: sh

     python3 -m pybel_tools service

After previously having uploaded your BEL graphs
.. code-block:: sh

     python3 -m pybel_tools upload "PATH_TO_YOUR_GRAPH_PICKLE"



