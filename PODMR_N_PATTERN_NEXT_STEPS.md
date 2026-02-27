# PODMR N-Pattern Next Steps

## Current Status
- PODMR backend accepts up to 4 patterns (`num_pattern()` path).
- Data model stores/analyzes N-pattern data in concrete attrs:
  - signal: `data0..data3`
  - reference: `data0ref..data3ref`
- Pattern-indexed accessors are available:
  - getters: `data(i)`, `data_ref(i)`
  - setters: `set_data(i, v)`, `set_data_ref(i, v)`
- SPODMR explicitly rejects generators where `num_pattern() != 2`.
- Plotting behavior is still effectively two-pattern oriented in complementary mode.
  - Current `concatenate` mode is aligned to pattern0/pattern1 behavior.

## Goal of Next Phase
Implement full user-facing N>2 support for:
1. pattern generation for selected PODMR methods,
2. plotting conversions/modes,
3. GUI/CLI controls and export behavior.

## 1) Generator Implementation (N>2 Methods)
- Pick target methods first (do not generalize all methods at once).
- For each target method:
  - override `PatternGenerator.num_pattern(params)` to return N (3 or 4),
  - generate all pattern variants via `generate_blocksN()`,
  - ensure read phases and pattern naming stay deterministic (`P{i}-{k}`, `read{i}-{k}`).
- Validate partial behavior:
  - `partial = -1`: all patterns,
  - `partial = k`: single pattern `k`.

## 2) Plot Conversion Spec (Decision Needed Before Coding)
Define canonical conversions for N-pattern data. Suggested minimum set:
- direct selections:
  - `data0`, `data1`, `data2`, `data3`,
  - `ref0`, `ref1`, `ref2`, `ref3` (or a generalized `refN` form).
- pairwise:
  - `data01`, `data23`,
  - `diff01`, `diff23`,
  - `normalize01`, `normalize23`.
- aggregate:
  - `average_all`,
  - optional `normalize_all` (define formula explicitly).

Also define:
- behavior when selected mode requires unavailable indices,
- behavior of `flipY` for pairwise modes beyond `01`,
- `refaverage` semantics for pairwise and all-pattern modes.

## 3) PODMR Data Plotting Logic Update
Update `PODMRData._get_ydata_complementary()` to:
- dispatch by new plotmode set,
- support pairwise index selection (`01`, `23`, and future generic form),
- avoid hardcoded `data0/data1` assumptions,
- return `(y0, y1)` consistently for dual-trace modes and `(y, None)` for single-trace modes.

Update related helpers:
- `_concat_xdata()` and head-timing handling where mode assumptions are currently two-pattern specific,
- sampling-rate logic if it is displayed in UI for non-2-pattern methods.

## 4) Param Dict and CLI
- Extend PODMR `plot.plotmode` choices in worker param dict.
- Update CLI help text and accepted values in `mahos_dq/cli/plot.py`.
- Keep existing legacy names unchanged for backward compatibility.

## 5) GUI Updates
In PODMR GUI:
- add new plotmode entries in UI (`podmr.ui` and generated `podmr.py`),
- ensure `partial` selector and plotmode auto-switch logic are N-aware,
- avoid assumptions that only `data0`/`data1` exist in plot color/legend logic.

Optional but recommended:
- dynamic enable/disable of plotmodes based on current `num_pattern`.

## 6) Export / Color / Marker Policy
- Generalize export parameters currently keyed as `color0/color1` and `marker0/marker1`.
- Keep old keys supported, but add scalable keys for N-pattern modes.
- Define consistent legend naming for pairwise/all-pattern modes.

## 7) Testing Plan
- Generator tests:
  - golden pattern tests for each new N-pattern method,
  - partial and all-pattern generation checks.
- Data/plot tests:
  - unit tests for each new plotmode formula,
  - invalid mode/index behavior tests.
- GUI tests:
  - start/run with N-pattern method,
  - basic receive-and-plot smoke tests,
  - plotmode selection tests.
- Backward compatibility:
  - existing 2-pattern tests must remain green,
  - old data files still load correctly.

## 8) Suggested Incremental Rollout
1. one N=4 method + backend formulas + CLI,
2. GUI support for new plotmodes,
3. additional methods,
4. cleanup/refactor of duplicated pairwise logic.
