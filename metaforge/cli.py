"""Command-line interface: run a meta-analysis from a CSV file without a server."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .service import analyze_csv


def _fmt(x) -> str:
    return "—" if x is None else f"{x:.3f}"


def _print_summary(out: dict) -> None:
    p, h = out["pooled"], out["heterogeneity"]
    m = out["measure"]
    print(f"\nMetaForge — {out['measure_label']} ({m}), k={out['k']} studies")
    model = out["model"] + (f", {out['tau2_method']}" if out["model"] == "random" else "")
    if out["knapp_hartung"]:
        model += ", Knapp-Hartung"
    print(f"Model: {model}\n")
    print(f"  Pooled {m}: {_fmt(p['estimate'])}  (95% CI {_fmt(p['ci_low'])} to {_fmt(p['ci_high'])})")
    print(f"  p-value:   {_fmt(p['p_value'])}")
    if p["pi_low"] is not None:
        print(f"  95% PI:    {_fmt(p['pi_low'])} to {_fmt(p['pi_high'])}")
    print(f"  Heterogeneity: I²={h['i2']:.0f}%  τ²={_fmt(h['tau2'])}  "
          f"Q={_fmt(h['q'])} (df={h['q_df']}, p={_fmt(h['q_p'])})")
    if out["egger"]:
        e = out["egger"]
        print(f"  Egger's test:  intercept={_fmt(e['intercept'])}, p={_fmt(e['p_value'])}")
    if out["trim_fill"] and out["trim_fill"]["k0"] > 0:
        t = out["trim_fill"]
        print(f"  Trim-and-fill: {t['k0']} imputed on the {t['side']}; "
              f"adjusted {m}={_fmt(t['adjusted_estimate'])}")
    if out["subgroups"]:
        s = out["subgroups"]
        print(f"  Subgroups:     Q_between={_fmt(s['q_between'])} (df={s['df']}, p={_fmt(s['p_value'])})")
        for g in s["groups"]:
            print(f"      - {g['subgroup']}: {m}={_fmt(g['estimate'])} "
                  f"[{_fmt(g['ci_low'])}, {_fmt(g['ci_high'])}], k={g['k']}, I²={g['i2']:.0f}%")
    print()


def _write_outputs(out: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, key in [("forest.svg", "forest_svg"), ("funnel.svg", "funnel_svg"),
                      ("leave_one_out.svg", "loo_forest_svg"), ("baujat.svg", "baujat_svg")]:
        if out.get(key):
            (out_dir / name).write_text(out[key])
    header = "study_label,subgroup,estimate,ci_low,ci_high,weight_pct,yi,se\n"
    lines = [
        f'"{s["label"]}",{s.get("subgroup") or ""},{s["estimate"]},{s["ci_low"]},'
        f'{s["ci_high"]},{s["weight_pct"]},{s["yi"]},{s["se"]}'
        for s in out["studies"]
    ]
    (out_dir / "estimates.csv").write_text(header + "\n".join(lines) + "\n")
    serialisable = {k: v for k, v in out.items() if not k.endswith("_svg")}
    (out_dir / "results.json").write_text(json.dumps(serialisable, indent=2))
    print(f"Wrote forest/funnel/leave_one_out/baujat SVGs, estimates.csv and results.json to {out_dir}/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="metaforge", description="Local-first pairwise meta-analysis.")
    parser.add_argument("csv", help="CSV file with one row per study (see README for columns).")
    parser.add_argument("--model", choices=["random", "fixed"], default="random")
    parser.add_argument("--tau2", choices=["REML", "DL", "PM"], default="REML", help="tau² estimator")
    parser.add_argument("--no-kh", action="store_true", help="disable the Knapp-Hartung adjustment")
    parser.add_argument("--out", metavar="DIR", help="write plots, estimates.csv and results.json here")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON to stdout")
    args = parser.parse_args(argv)

    path = Path(args.csv)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2
    try:
        out = analyze_csv(
            path.read_text(),
            model=args.model,
            tau2_method=args.tau2,
            knapp_hartung=not args.no_kh,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({k: v for k, v in out.items() if not k.endswith("_svg")}, indent=2))
    else:
        _print_summary(out)
    if args.out:
        _write_outputs(out, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
