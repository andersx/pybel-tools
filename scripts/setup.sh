#!/usr/bin/env bash

python3 -m pybel_tools manage role add "admin"
python3 -m pybel_tools manage role add "scai"

python3 -m pybel_tools manage user add "cthoyt@gmail.com" "pybeladmin"
python3 -m pybel_tools manage user make_admin "cthoyt@gmail.com"

python3 -m pybel_tools manage user add "scai@example.com" "pybeltest"
python3 -m pybel_tools manage user add_role "scai@example.com" "scai"

python3 -m pybel_tools manage user add "test@example.com" "pybeltest"
