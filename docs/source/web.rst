Web Services
============

Running with the Command Line
-----------------------------

Running the PyBEL Tools Flask application allows you to interact with your networks and apply filters/algorithms.
Multiple services are available. Use :code:`--help` for a description.

.. code-block:: sh

    $ python3 -m pybel_tools web

After previously having uploaded your BEL graphs

.. code-block:: sh

    $ python3 -m pybel_tools upload "PATH_TO_YOUR_GRAPH_PICKLE"

Setting up with Docker
----------------------
- http://phusion.github.io/baseimage-docker/
- https://penandpants.com/2014/03/09/docker-via-homebrew/

.. automodule:: pybel_tools.web

.. automodule:: pybel_tools.service

