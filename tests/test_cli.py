"""Tests for the command-line argument parser."""

import sys

import pytest

from amine.arg_parser import parse_arguments


def _parse(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["amine", *argv])
    return parse_arguments("amine")


def test_required_arguments(monkeypatch):
    arg = _parse(monkeypatch, ["-x", "expr.csv", "-g", "0"])
    assert str(arg.expvalue_file) == "expr.csv"
    assert arg.gene_col == 0


def test_nb_modules_default_is_none(monkeypatch):
    arg = _parse(monkeypatch, ["-x", "expr.csv", "-g", "0"])
    assert arg.nb_modules_to_find is None


def test_nb_modules_short_flag(monkeypatch):
    arg = _parse(monkeypatch, ["-x", "expr.csv", "-g", "0", "-k", "3"])
    assert arg.nb_modules_to_find == 3


def test_nb_modules_long_flag(monkeypatch):
    arg = _parse(monkeypatch, ["-x", "expr.csv", "-g", "0", "--nb_modules", "5"])
    assert arg.nb_modules_to_find == 5


def test_missing_required_argument_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["amine", "-g", "0"])
    with pytest.raises(SystemExit):
        parse_arguments("amine")
