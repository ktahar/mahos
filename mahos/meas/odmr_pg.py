#!/usr/bin/env python3

"""
PG sequence for ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import math

from mahos.msgs.inst.pg_msgs import Block, Blocks, TriggerType
from mahos.msgs.pulse_msgs import PulsePattern


class ODMRPGMixin(object):
    """PG configuration for ODMR.

    Required attributes:
    - conf
        - pg_freq_cw
    - pg
    - _analog_pd
    - _block_base
    - _channel_remap
    - _minimum_block_length

    """

    def _adjust_block(self, block: Block, index: int):
        """Mutate block so that block's total_length is integer multiple of block base."""

        duration = block.total_length()
        if M := duration % self._block_base:
            ch, d = block.pattern[index].channels, block.pattern[index].duration
            block.pattern[index] = (ch, d + self._block_base - M)

    def configure_pg_CW_analog(self, params: dict, trigger_type: TriggerType) -> bool:
        freq = self.conf["pg_freq_cw"]
        # gate / trigger pulse width
        unit = round(freq * 1.0e-6)
        window = round(freq * params["timing"]["time_window"])
        gate_delay = round(freq * params["timing"].get("gate_delay", 0.0))
        delay = round(freq * params.get("delay", 0.0))
        bg_delay = round(freq * params.get("background_delay", 0.0))
        background = params.get("background", False)
        if background and gate_delay:
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    (("laser", "mw"), gate_delay),
                    (("laser", "mw", "gate"), unit),
                    # As measurement window is defined by DAQ sampling side,
                    # here we give long enough laser / mw pulse width (no "window - unit" below).
                    (("laser", "mw"), window),
                    (None, max(unit, bg_delay)),
                    ("laser", gate_delay),
                    (("laser", "gate"), unit),
                    ("laser", window),
                    ("trigger", unit),
                ],
                trigger=True,
            )
        elif background:  # no gate_delay
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    ("gate", unit),
                    (("laser", "mw"), window),
                    (None, max(unit, bg_delay)),
                    ("gate", unit),
                    ("laser", window),
                    ("trigger", unit),
                ],
                trigger=True,
            )
        elif gate_delay:  # no background
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    (("laser", "mw"), gate_delay),
                    (("laser", "mw", "gate"), unit),
                    (("laser", "mw"), window),
                    ("trigger", unit),
                ],
                trigger=True,
            )
        else:  # no gate_delay, no background
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    ("gate", unit),
                    (("laser", "mw"), window),
                    ("trigger", unit),
                ],
                trigger=True,
            )
        self._adjust_block(b, 0)
        blocks = Blocks([b])
        if self._channel_remap is not None:
            blocks = blocks.replace(self._channel_remap)
        blocks = blocks.simplify()
        success = self.pg.configure_blocks(blocks, freq, trigger_type=trigger_type, n_runs=1)
        if success:
            self.pulse_pattern = PulsePattern(blocks, freq)
        return success

    def configure_pg_pulse_analog(self, params: dict, trigger_type: TriggerType) -> bool:
        freq = self.conf["pg_freq_pulse"]
        min_len = self._minimum_block_length
        # gate / trigger pulse width
        delay = round(freq * params.get("delay", 0.0))
        bg_delay = round(freq * params.get("background_delay", 0.0))
        background = params.get("background", False)

        laser_delay, laser_width, mw_delay, mw_width, trigger_width = [
            round(params["timing"][k] * freq)
            for k in ("laser_delay", "laser_width", "mw_delay", "mw_width", "trigger_width")
        ]
        if mw_delay < trigger_width:
            self.logger.error("mw_delay >= trigger_width must be satisfied.")
            return False

        seq_length = sum(
            params["timing"][k] for k in ("laser_delay", "laser_width", "mw_delay", "mw_width")
        )

        # convert time_window and gate_delay to number of sequence repetitions
        # round-up because total sequence a bit shorter than time_window can be a problem,
        # but a bit longer sequence is not.
        burst_num = math.ceil(params["timing"]["time_window"] / seq_length)
        gate_delay_num = math.ceil(params["timing"].get("gate_delay", 0.0) / seq_length)
        self.logger.info(f"Burst Num: {burst_num} Gate Delay Num: {gate_delay_num}")

        blocks = []
        if delay:
            blk_delay = Block(
                "Delay",
                [
                    (None, max(delay, min_len)),
                ],
                trigger=True,
            )
            self._adjust_block(blk_delay, 0)
            blocks.append(blk_delay)

        if gate_delay_num:
            blk_gate_delay = Block(
                "Gate-Delay",
                [
                    ("laser", laser_width),
                    (None, mw_delay),
                    ("mw", mw_width),
                    (None, laser_delay),
                ],
                Nrep=gate_delay_num,
                trigger=not bool(delay),
            )
            self._adjust_block(blk_gate_delay, 0)
            blocks.append(blk_gate_delay)

        blk_gate = Block(
            "Gate",
            [
                ("laser", laser_width),
                ("gate", trigger_width),
                (None, mw_delay - trigger_width),
            ],
            trigger=not (bool(delay) or bool(gate_delay_num)),
        )
        self._adjust_block(blk_gate, 0)
        blocks.append(blk_gate)

        blk_main = Block(
            "Main",
            [
                ("mw", mw_width),
                (None, laser_delay),
                ("laser", laser_width),
                (None, mw_delay),
            ],
            Nrep=burst_num,
        )
        self._adjust_block(blk_main, 0)
        blocks.append(blk_main)

        if background:
            if bg_delay:
                blk_bg_delay = Block(
                    "BG-Delay",
                    [
                        (None, max(bg_delay, min_len)),
                    ],
                )
                self._adjust_block(blk_bg_delay, 0)
                blocks.append(blk_bg_delay)

            if gate_delay_num:
                blk_bg_gate_delay = Block(
                    "BG-Gate-Delay",
                    [
                        ("laser", laser_width),
                        (None, mw_delay + mw_width + laser_delay),
                    ],
                    Nrep=gate_delay_num,
                )
                self._adjust_block(blk_bg_gate_delay, 0)
                blocks.append(blk_bg_gate_delay)

            blk_bg_gate = Block(
                "BG-Gate",
                [
                    ("laser", laser_width),
                    ("gate", trigger_width),
                    (None, mw_delay - trigger_width),
                ],
            )
            self._adjust_block(blk_bg_gate, 0)
            blocks.append(blk_bg_gate)

            blk_bg_main = Block(
                "BG-Main",
                [
                    (None, mw_width + laser_delay),
                    ("laser", laser_width),
                    (None, mw_delay),
                ],
                Nrep=burst_num,
            )
            self._adjust_block(blk_bg_main, 0)
            blocks.append(blk_bg_main)

        blk_trigger = Block(
            "Trigger",
            [
                ("trigger", max(trigger_width, min_len)),
            ],
        )
        self._adjust_block(blk_trigger, 0)
        blocks.append(blk_trigger)

        blocks = Blocks(blocks)
        if self._channel_remap is not None:
            blocks = blocks.replace(self._channel_remap)
        blocks = blocks.simplify()
        success = self.pg.configure_blocks(blocks, freq, trigger_type=trigger_type, n_runs=1)
        if success:
            self.pulse_pattern = PulsePattern(blocks, freq)
        return success

    def configure_pg_CW_apd(self, params: dict, trigger_type: TriggerType) -> bool:
        freq = self.conf["pg_freq_cw"]
        # gate / trigger pulse width
        unit = round(freq * 1.0e-6)
        window = round(freq * params["timing"]["time_window"])
        gate_delay = round(freq * params["timing"].get("gate_delay", 0.0))
        delay = round(freq * params.get("delay", 0.0))
        bg_delay = round(freq * params.get("background_delay", 0.0))
        background = params.get("background", False)
        if background and gate_delay:
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    (("laser", "mw"), gate_delay),
                    # here we define measurement window using interval between gate pulses
                    (("laser", "mw", "gate"), unit),
                    (("laser", "mw"), window - unit),
                    (("laser", "mw", "gate"), unit),
                    (None, max(unit, bg_delay)),
                    ("laser", gate_delay),
                    (("laser" "gate"), unit),
                    ("laser", window - unit),
                    (("laser" "gate"), unit),
                    ("trigger", unit),
                ],
                trigger=True,
            )
        elif background:  # no gate_delay
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    ("gate", unit),
                    # here we define measurement window using laser / mw pulse width
                    # (no "window - unit" below)
                    (("laser", "mw"), window),
                    ("gate", unit),
                    (None, max(unit, bg_delay)),
                    ("gate", unit),
                    ("laser", window),
                    (("gate", "trigger"), unit),
                ],
                trigger=True,
            )
        elif gate_delay:  # no background
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    (("laser", "mw"), gate_delay),
                    (("laser", "mw", "gate"), unit),
                    (("laser", "mw"), window - unit),
                    (("laser", "mw", "gate"), unit),
                    ("trigger", unit),
                ],
                trigger=True,
            )
        else:  # no gate_delay, no background
            b = Block(
                "CW-ODMR",
                [
                    (None, max(unit, delay)),
                    ("gate", unit),
                    (("laser", "mw"), window),
                    (("gate", "trigger"), unit),
                ],
                trigger=True,
            )
        self._adjust_block(b, 0)
        blocks = Blocks([b])
        if self._channel_remap is not None:
            blocks = blocks.replace(self._channel_remap)
        blocks = blocks.simplify()
        success = self.pg.configure_blocks(blocks, freq, trigger_type=trigger_type, n_runs=1)
        if success:
            self.pulse_pattern = PulsePattern(blocks, freq)
        return success

    def _make_blocks_pulse_apd_nobg(
        self, delay, laser_delay, laser_width, mw_delay, mw_width, trigger_width, burst_num
    ):
        min_len = self._minimum_block_length

        init = Block(
            "INIT",
            [
                (None, max(delay, min_len - laser_width - mw_delay)),
                ("laser", laser_width),
                ("gate", trigger_width),
                (None, mw_delay - trigger_width),
            ],
            trigger=True,
        )

        main = Block(
            "MAIN",
            [
                ("mw", mw_width),
                (None, laser_delay),
                ("laser", laser_width),
                (None, mw_delay),
            ],
            Nrep=burst_num,
        )

        final = Block(
            "FINAL",
            [
                (["gate", "trigger"], trigger_width),
                (None, max(0, min_len - trigger_width)),
            ],
        )

        for b in (init, final):
            self._adjust_block(b, 0)
        self._adjust_block(main, -1)
        blocks = Blocks([init, main, final])
        if self._channel_remap is not None:
            blocks = blocks.replace(self._channel_remap)
        return blocks.simplify()

    def _make_blocks_pulse_apd_bg(
        self,
        delay,
        bg_delay,
        laser_delay,
        laser_width,
        mw_delay,
        mw_width,
        trigger_width,
        burst_num,
    ):
        min_len = self._minimum_block_length

        init = Block(
            "INIT",
            [
                (None, max(delay, min_len - laser_width - mw_delay)),
                ("laser", laser_width),
                ("gate", trigger_width),
                (None, mw_delay - trigger_width),
            ],
            trigger=True,
        )

        main = Block(
            "MAIN",
            [
                ("mw", mw_width),
                (None, laser_delay),
                ("laser", laser_width),
                (None, mw_delay),
            ],
            Nrep=burst_num,
        )

        final = Block(
            "FINAL",
            [
                ("gate", trigger_width),
                (None, max(0, min_len - trigger_width)),
            ],
        )

        init_bg = Block(
            "INIT-BG",
            [
                (None, max(bg_delay, min_len - laser_width - mw_delay)),
                ("laser", laser_width),
                ("gate", trigger_width),
                (None, mw_delay - trigger_width),
            ],
        )

        main_bg = Block(
            "MAIN-BG",
            [
                (None, mw_width),
                (None, laser_delay),
                ("laser", laser_width),
                (None, mw_delay),
            ],
            Nrep=burst_num,
        )

        final_bg = Block(
            "FINAL-BG",
            [
                (["gate", "trigger"], trigger_width),
                (None, max(0, min_len - trigger_width)),
            ],
        )

        for b in (init, final, init_bg, final_bg):
            self._adjust_block(b, 0)
        for b in (main, main_bg):
            self._adjust_block(b, -1)
        blocks = Blocks([init, main, final, init_bg, main_bg, final_bg])
        if self._channel_remap is not None:
            blocks = blocks.replace(self._channel_remap)
        return blocks.simplify()

    def configure_pg_pulse_apd(self, params: dict, trigger_type: TriggerType) -> bool:
        freq = self.conf["pg_freq_pulse"]
        delay = round(freq * params.get("delay", 0.0))
        bg_delay = round(freq * params.get("background_delay", 0.0))
        laser_delay, laser_width, mw_delay, mw_width, trigger_width = [
            round(params["timing"][k] * freq)
            for k in ("laser_delay", "laser_width", "mw_delay", "mw_width", "trigger_width")
        ]
        burst_num = params["timing"]["burst_num"]

        if mw_delay < trigger_width:
            self.logger.error("mw_delay >= trigger_width must be satisfied.")
            return False

        if params.get("background", False):
            blocks = self._make_blocks_pulse_apd_bg(
                delay,
                bg_delay,
                laser_delay,
                laser_width,
                mw_delay,
                mw_width,
                trigger_width,
                burst_num,
            )
        else:
            blocks = self._make_blocks_pulse_apd_nobg(
                delay, laser_delay, laser_width, mw_delay, mw_width, trigger_width, burst_num
            )

        success = self.pg.configure_blocks(blocks, freq, trigger_type=trigger_type, n_runs=1)
        if success:
            self.pulse_pattern = PulsePattern(blocks, freq)
        return success

    def configure_pg(self, params: dict, label: str, trigger_type: TriggerType) -> bool:
        if not (self.pg.stop() and self.pg.clear()):
            return False
        if self._pd_analog:
            if label != "pulse":
                return self.configure_pg_CW_analog(params, trigger_type)
            else:
                return self.configure_pg_pulse_analog(params, trigger_type)
        else:
            if label != "pulse":
                return self.configure_pg_CW_apd(params, trigger_type)
            else:
                return self.configure_pg_pulse_apd(params, trigger_type)
