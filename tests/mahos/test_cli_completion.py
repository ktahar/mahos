#!/usr/bin/env python3

from mahos.cli import main


def test_completion_parser_parses_top_level_commands():
    parser = main.build_completion_parser()

    run_args = parser.parse_args(["run", "localhost::log"])
    assert run_args.command == "run"
    assert run_args.node == "localhost::log"

    log_args = parser.parse_args(["log"])
    assert log_args.command == "log"
    assert log_args.node == "log"

    ls_args = parser.parse_args(["ls", "-i"])
    assert ls_args.command == "ls"
    assert ls_args.inst is True


def test_completion_parser_parses_data_subcommands():
    parser = main.build_completion_parser()

    note_args = parser.parse_args(["data", "note", "result.h5"])
    assert note_args.command == "data"
    assert note_args.data_command == "note"
    assert note_args.names == ["result.h5"]

    print_args = parser.parse_args(["data", "print", "result.h5"])
    assert print_args.command == "data"
    assert print_args.data_command == "print"
    assert print_args.names == ["result.h5"]


def test_completion_parser_parses_data_plot_subcommand():
    parser = main.build_completion_parser()

    odmr_args = parser.parse_args(["data", "plot", "odmr", "result.h5"])
    assert odmr_args.command == "data"
    assert odmr_args.data_command == "plot"
    assert odmr_args.func.__name__ == "plot_odmr"
    assert odmr_args.names == ["result.h5"]
