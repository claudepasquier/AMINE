#!/usr/bin/env python3

"""
+-------------------------------------------------------------------------------------+
| This file is part of AMINE                                                          |
|                                                                                     |
| AMINE is free software: you can redistribute it and/or modify it under the terms of |
| the GNU General Public License as published by the Free Software Foundation, either |
| version 3 of the License, or (at your option) any later version.                    |
| You should have received a copy of the GNU General Public License along with AMINE. |
| If not, see <http://www.gnu.org/licenses/>.                                         |
|                                                                                     |
| Author: Claude Pasquier (I3S Laboratory, CNRS, Université Côte d'Azur)              |
| Contact: claude.pasquier@univ-cotedazur.fr                                          |
| Created on decembre 20, 2022                                                        |
+-------------------------------------------------------------------------------------+

Script used to import data.

By default every supported species is downloaded. For deployments it is usually
preferable to download only the species that will actually be served, e.g.::

    python -m amine.download_data --specie human
    python -m amine.download_data --specie human --specie mouse --skip-biogrid
"""

import argparse
import os
import urllib.request

import yaml
from tqdm import tqdm

from .parameters import Param


class ProgressBar:
    """
    Class encapsulating all variables and methods needed for the progress bar.

    This is a drop-in replacement for the former ``progressbar2`` based class,
    implemented with ``tqdm``.  It is used as the ``reporthook`` argument of
    ``urllib.request.urlretrieve``.
    """

    def __init__(self, prefix):
        self.prefix = prefix
        self.pbar = None

    def __call__(self, block_num, block_size, total_size):
        if not self.pbar:
            if total_size > 0:
                self.pbar = tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=self.prefix,
                )
            else:
                self.pbar = tqdm(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=self.prefix,
                )
        downloaded = block_num * block_size
        if total_size < 0 or (total_size > 0 and downloaded < total_size):
            self.pbar.update(block_size)
        else:
            self.pbar.update(max(0, total_size - self.pbar.n))
            self.pbar.close()


def _load_config() -> None:
    """Load the program parameters from the 'config.yaml' file if it exists."""
    try:
        with open("config.yaml") as f:
            params = yaml.safe_load(f)
        for key, value in params.items():
            setattr(Param, key, value)
        print("Parameters read from 'config.yaml' file.")
    except yaml.YAMLError:
        print("Problem occured when reading 'config.yaml'.")
        print("Using default parameters.")
    except FileNotFoundError:
        pass


def _download_string(specie_name: str) -> None:
    """Download the three STRING files (links, info, aliases) for a species."""
    print(f"Data from String database version {Param.string_version} ({specie_name})")
    for getter, kind in (
        (Param.get_string_ppi_file, "protein.links.detailed"),
        (Param.get_string_info_file, "protein.info"),
        (Param.get_string_alias_file, "protein.aliases"),
    ):
        local_filename, local_path = getter(specie_name)
        distant_name = (
            f"https://stringdb-static.org/download/{kind}.v{Param.string_version}/"
            f"{local_filename}"
        )
        urllib.request.urlretrieve(
            distant_name, local_path, ProgressBar(local_filename)
        )


def ensure_species_data(specie: str) -> None:
    """Download the STRING files for ``specie`` if they are missing.

    This is used by the web application to fetch a species on demand, so that
    a job submitted for a species whose data has not been pre-downloaded still
    succeeds. Existing files are left untouched.
    """
    (Param.datadir / "real" / "ppi").mkdir(parents=True, exist_ok=True)
    for getter, kind in (
        (Param.get_string_ppi_file, "protein.links.detailed"),
        (Param.get_string_info_file, "protein.info"),
        (Param.get_string_alias_file, "protein.aliases"),
    ):
        local_filename, local_path = getter(specie)
        if os.path.isfile(local_path):
            continue
        distant_name = (
            f"https://stringdb-static.org/download/{kind}.v{Param.string_version}/"
            f"{local_filename}"
        )
        urllib.request.urlretrieve(
            distant_name, local_path, ProgressBar(local_filename)
        )


def _download_biogrid() -> None:
    """Download the BioGRID archive."""
    print(f"Data from BIOGRID database version {Param.biogrid_version}")
    local_filename, local_path = Param.get_biogrid_file()
    distant_name = (
        "https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive/"
        f"BIOGRID-{Param.biogrid_version}/{local_filename}"
    )
    pbar = ProgressBar(local_filename)
    urllib.request.urlretrieve(distant_name, local_path, pbar)
    if pbar.pbar is not None:
        pbar.pbar.close()


def _download_intact() -> None:
    """Download the IntAct archive."""
    print("Data from IntAct database")
    local_filename, local_path = Param.get_intact_file()
    distant_name = (
        f"https://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/{local_filename}"
    )
    urllib.request.urlretrieve(distant_name, local_path, ProgressBar(local_filename))


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Download AMINE datasets.")
    parser.add_argument(
        "-s",
        "--specie",
        dest="species",
        action="append",
        choices=list(Param.specie2id),
        help=(
            "species to download (repeatable). If omitted, every supported "
            "species is downloaded."
        ),
    )
    parser.add_argument(
        "--skip-biogrid",
        dest="skip_biogrid",
        action="store_true",
        help="do not download the BioGRID archive",
    )
    parser.add_argument(
        "--skip-intact",
        dest="skip_intact",
        action="store_true",
        help="do not download the IntAct archive",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_arguments()
    _load_config()

    species = args.species or list(Param.specie2id)
    # ``urlretrieve`` does not create parent directories, so make sure the
    # target directory exists before downloading.
    (Param.datadir / "real" / "ppi").mkdir(parents=True, exist_ok=True)
    print(f"Downloading files to {Param.datadir}")

    for specie_name in species:
        _download_string(specie_name)

    if not args.skip_biogrid:
        _download_biogrid()

    if not args.skip_intact:
        _download_intact()


if __name__ == "__main__":
    main()
