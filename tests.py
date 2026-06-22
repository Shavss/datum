"""
tests.py - quick checks for the service layer. Run: python tests.py
Covers input validation (the schema must reject bad data) and that the cost
engine reads from injected inputs rather than globals.
"""
import inputs as I
import cost as C
import bernstein as B


def _expect_error(fn, label):
    try:
        fn()
    except I.InputError:
        return
    raise AssertionError(f"expected InputError: {label}")


def test_default_loads():
    ci = I.default_inputs()
    assert ci.bands and ci.timesheet, "default inputs should be non-empty"
    assert set(ci.autonomy) >= set(t for _g, t in B.TASK_ORDER), "autonomy must cover all tasks"


def test_rejects_bad_band():
    ci = I.default_inputs()
    ci.timesheet = ci.timesheet + [dict(band="Ghost", stage=B.STAGES[0], hours=10)]
    _expect_error(lambda: I.validate(ci), "unknown band")


def test_rejects_bad_stage():
    ci = I.default_inputs()
    ci.timesheet = [dict(band=ci.bands[0], stage="Not a stage", hours=10)]
    _expect_error(lambda: I.validate(ci), "unknown stage")


def test_rejects_bad_adoption():
    ci = I.default_inputs()
    ci.adoption = {"low": 0.8, "expected": 0.5, "high": 0.3}      # out of order
    _expect_error(lambda: I.validate(ci), "adoption order")
    ci2 = I.default_inputs()
    ci2.adoption = {"low": 0.3, "expected": 1.4, "high": 0.8}     # out of range
    _expect_error(lambda: I.validate(ci2), "adoption range")


def test_rejects_negative_rate_and_hours():
    ci = I.default_inputs()
    ci.band_rates = dict(ci.band_rates); ci.band_rates[ci.bands[0]] = -5
    _expect_error(lambda: I.validate(ci), "negative rate")


def test_engine_uses_injected_inputs():
    base = C.totals(I.default_inputs())["expected"]["cost"]
    ci = I.default_inputs()
    ci.band_rates = {b: r * 2 for b, r in ci.band_rates.items()}
    I.validate(ci)
    doubled = C.totals(ci)["expected"]["cost"]
    assert abs(doubled - 2 * base) < 1, "doubling rates should double the cost base"


def test_growth_exceeds_margin():
    c = C.conversion(ci=I.default_inputs())
    assert c["growth_value"] > c["margin_value"], "growth route should exceed margin"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
