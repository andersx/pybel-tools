Command Line Cookbook
=====================

Pickling lots of BEL scripts
----------------------------
All of the BEL scripts in the current working directory (and sub-directories) can be pickled in-place with the
following command (add :code:`-d` to specify a different directory)

.. code-block:: sh

    $ python3 -m pybel_tools io convert -d ~/bms/aetionomy/

Uploading a Network
-------------------
A single network stored as a pickle can quickly be uploaded.

.. code::

    $ python3 -m pybel_tools io upload /path/to/my_network.gpickle

Multiple networks in a given directory and sub-directories can be uploaded by adding the :code:`-r` tag.

.. code::

    $ python3 -m pybel_tools io upload ~/bms/aetionomy/  -r

