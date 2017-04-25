Web Services
============

Running from the Command Line
-----------------------------
PyBEL Tools deploys a Flask web application that allows you to interact with your networks and apply filters/algorithms.

Multiple services are available. Use :code:`--help` for a description. To run the web services, type:

.. code-block:: sh

    $ python3 -m pybel_tools web

By default, Flask deploys on ``localhost`` at port ``5000``. These can be changed respectively with the ``--host`` and
``--port`` arguments. Additionally, logging can be shown with ``-v``.

Setting up with Docker
----------------------
A simple `Dockerfile <https://github.com/pybel/pybel-tools/blob/develop/Dockerfile>`_ is included in the root-level
directory on the GitHub repository. This Dockerfile is inspired by the tutorials at http://containertutorials.com/docker-compose/flask-simple-app.html.
and https://www.digitalocean.com/community/tutorials/docker-explained-how-to-containerize-python-web-applications.

Links:

- Running docker on mac: https://penandpants.com/2014/03/09/docker-via-homebrew/
- Using baseimage: http://phusion.github.io/baseimage-docker/


.. automodule:: pybel_tools.web
