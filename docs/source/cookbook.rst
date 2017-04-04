Command Line Cookbook
=====================

Uploading a Network
-------------------
Networks stored as pickles can quickly be uploaded with the command line interface using:

.. code-block::

    python3 -m pybel_tools upload "/path/to/my_network.gpickle"

Network pickles can easily be produced using the PyBEL command line tool:

.. code-block::

    python3 -m pybel convert "/path/to/my_bel.bel" --pickle "/path/to/my_network.gpickle"

Or, the network can be directly uploaded from the PyBEL conversion script:

.. code-block::

    python3 -m pybel convert "/path/to/my_bel.bel" --store-default
