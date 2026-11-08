#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Module containing the class Param."""

import os
import pathlib


class Param:
    """Group program parameters."""

    project_name = 'amine'
    os.environ["PYTHONHASHSEED"] = '1'

    # Datasets are located in 'datadir'
    # datadir is either the directory 'data' located in the current directory
    # or a directory specified with the environment variable AMINE_DATA

    try:
        datadir = pathlib.Path(os.path.expandvars(
            os.environ["AMINE_DATA"]))
    except KeyError:
        datadir = pathlib.Path(
            pathlib.Path(__file__).parent, 'data')

    precomputed_models_dir = pathlib.Path(datadir, 'models')

    specie2id = {'human': '9606', 'mouse': '10090', 'drosophila' : '7227', 'Caenorhabditis elegans': '6239'}
    string_version = 'v11.0'

    @staticmethod
    def get_string_ppi_file(specie):
        """Get path to interaction file."""
        filename = "{}.protein.links.detailed.{}.txt.gz".format(Param.specie2id[specie], Param.string_version)
        return os.path.join(Param.datadir, filename)

    @staticmethod
    def get_string_info_file(specie):
        """Get path to protein information file."""
        filename = "{}.protein.info.{}.txt.gz".format(Param.specie2id[specie], Param.string_version)
        return os.path.join(Param.datadir, filename)

    @staticmethod
    def get_string_alias_file(specie):
        """Get path to protein alias file."""
        filename = "{}.protein.aliases.{}.txt.gz".format(Param.specie2id[specie], Param.string_version)
        return os.path.join(Param.datadir, filename)

    @staticmethod
    def get_node2vec_model(specie):
        """Get path to model file."""
        filename = "{}.{}.model".format(Param.specie2id[specie], Param.string_version)
        return os.path.join(Param.precomputed_models_dir, filename)
