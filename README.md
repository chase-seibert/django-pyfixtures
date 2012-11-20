django-pyfixtures
=================

Using the regular Django `dumpdata` command, pyfixtures will generate a python file that contains all the code necessary to re-constitute that data in an empty database. You can take that code and refactor it into something you maintain going forward, or you can re-generate it from a target database when needed.