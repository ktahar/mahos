#!/usr/bin/env python3

import subprocess
import sys
import textwrap

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


def test_completion_parser_does_not_import_heavy_runtime_dependencies():
    script = textwrap.dedent(
        """
        import sys

        before = set(sys.modules)
        from mahos.cli import main
        main.build_completion_parser()
        imported = sorted(set(sys.modules) - before)

        heavy_prefixes = (
            "IPython",
            "h5py",
            "matplotlib",
            "networkx",
            "numpy",
            "scipy",
            "zmq",
            "mahos.cli.threaded_nodes",
        )

        heavy_imports = []
        for module in imported:
            for prefix in heavy_prefixes:
                if module == prefix or module.startswith(prefix + "."):
                    heavy_imports.append(module)

        non_cli_mahos = [
            module for module in imported if module.startswith("mahos.")
            and not (module == "mahos.cli" or module.startswith("mahos.cli."))
        ]
        non_cli_mahos_dq = [
            module for module in imported if module.startswith("mahos_dq.")
            and not (module == "mahos_dq.cli" or module.startswith("mahos_dq.cli."))
        ]

        if heavy_imports or non_cli_mahos or non_cli_mahos_dq:
            if heavy_imports:
                print("heavy imports:", ", ".join(sorted(set(heavy_imports))), file=sys.stderr)
            if non_cli_mahos:
                print("non-cli mahos imports:", ", ".join(non_cli_mahos), file=sys.stderr)
            if non_cli_mahos_dq:
                print("non-cli mahos_dq imports:", ", ".join(non_cli_mahos_dq), file=sys.stderr)
            raise SystemExit(1)
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr
