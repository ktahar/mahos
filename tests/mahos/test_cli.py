#!/usr/bin/env python3

from types import SimpleNamespace

from mahos.cli import data, main


def test_main_no_command_prints_usage(monkeypatch, capsys):
    monkeypatch.delenv("_ARGCOMPLETE", raising=False)
    monkeypatch.setattr(main.sys, "argv", ["mahos"])

    assert main.main() == 1
    out = capsys.readouterr().out
    assert "usage: mahos COMMAND args" in out


def test_main_dispatches_run_prefix(monkeypatch):
    monkeypatch.delenv("_ARGCOMPLETE", raising=False)
    monkeypatch.setattr(main.sys, "argv", ["mahos", "r", "localhost::log"])

    called = []

    def fake_import_module(name: str):
        if name != "mahos.cli.run":
            raise AssertionError(f"unexpected module import: {name}")
        return SimpleNamespace(main=lambda args: called.append(args) or 42)

    monkeypatch.setattr(main.importlib, "import_module", fake_import_module)

    assert main.main() == 42
    assert called == [["localhost::log"]]


def test_main_dispatches_data_prefix(monkeypatch):
    monkeypatch.delenv("_ARGCOMPLETE", raising=False)
    monkeypatch.setattr(main.sys, "argv", ["mahos", "d", "note", "result.h5"])

    called = []

    def fake_import_module(name: str):
        if name != "mahos.cli.data":
            raise AssertionError(f"unexpected module import: {name}")
        return SimpleNamespace(main=lambda args: called.append(args) or 7)

    monkeypatch.setattr(main.importlib, "import_module", fake_import_module)

    assert main.main() == 7
    assert called == [["note", "result.h5"]]


def test_data_no_subcommand_prints_usage(capsys):
    assert data.main([]) == 1
    out = capsys.readouterr().out
    assert "usage: mahos data COMMAND args" in out


def test_data_dispatches_print_prefix(monkeypatch):
    called = []

    def fake_import_module(name: str):
        if name != "mahos.cli.data_print":
            raise AssertionError(f"unexpected module import: {name}")
        return SimpleNamespace(main=lambda args: called.append(args) or 9)

    monkeypatch.setattr(data.importlib, "import_module", fake_import_module)

    assert data.main(["pr", "result.h5"]) == 9
    assert called == [["result.h5"]]
