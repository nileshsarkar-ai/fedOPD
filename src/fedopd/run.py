"""Thin CLI over the fedOPD modules: one process = one run = one results/*.json.

    python -m src.fedopd.run --method fedavg --target delta --seed 0
    python -m src.fedopd.run --method fedprox --mu 0.01 --ft-epochs 3 --seed 2

Methods: naive | seasonal (via te_df) | local | central | fedavg | fedprox.
--ft-epochs > 0 additionally evaluates the personalised (+ft) variant of a fed run.
Every JSON carries config, metrics, R-01 on the same points, seed, git sha, duration.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from src.fedopd import data, fed, evaluate
from src.fedopd.model import Forecaster


def git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=data.ROOT).stdout.strip()
    except Exception:
        return "?"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True,
                    choices=["naive", "seasonal", "local", "central", "fedavg", "fedprox", "selective"])
    ap.add_argument("--target", default="delta", choices=["level", "delta"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--rounds", type=int, default=40)
    ap.add_argument("--local-epochs", type=int, default=1)
    ap.add_argument("--epochs", type=int, default=40)        # local/central budget = rounds*E
    ap.add_argument("--mu", type=float, default=0.01)
    ap.add_argument("--ft-epochs", type=int, default=0)
    ap.add_argument("--weighting", default="n", choices=["n", "equal", "sqrt"])
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--depts-mode", default="stable18")
    ap.add_argument("--min-coverage", type=float, default=0.5)
    ap.add_argument("--panel-min-months", type=int, default=96)
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--tag", default="")                     # extra label for sensitivity runs
    ap.add_argument("--out-dir", default=str(data.ROOT / "results"))
    a = ap.parse_args(argv)

    t0 = time.time()
    np.random.seed(a.seed)
    ds = data.build_all(a.depts_mode, a.min_coverage, a.panel_min_months, window=a.window)
    cd = data.per_client(ds)
    nf, te_df, Xte, nl = ds["n_features"], ds["te_df"], ds["Xte"], ds["n_lags"]
    metrics, extra = {}, {}

    if a.method == "naive":
        metrics = evaluate.naive_bar(te_df)
    elif a.method == "seasonal":
        # reconstruct raw t-12 from the scaled lag-0 column (lags are t-12..t-1; col 0 is t-12)
        assert a.window >= 12, "seasonal baseline needs lag-12 in the window"
        raw = Xte[:, a.window - 12] * te_df["sd"].values + te_df["mean"].values
        metrics = evaluate.score_raw(te_df, raw)
    elif a.method == "central":
        m = fed.train_centralised(ds["Xtr"], ds["ytr"], nf, a.target, a.epochs, a.lr, seed=a.seed,
                                  n_lags=nl)
        metrics = evaluate.score_scaled(te_df, m.predict(Xte))
    elif a.method == "local":
        models = fed.train_local_only(cd, nf, a.target, a.epochs, a.lr, seed=a.seed, n_lags=nl)
        metrics = evaluate.score_scaled(te_df, fed.predict_per_client(models, te_df, Xte))
    else:                                                    # fedavg / fedprox / selective
        mu = a.mu if a.method == "fedprox" else 0.0
        glob, hist = fed.run_federated(cd, nf, a.target, a.rounds, a.local_epochs, a.lr,
                                       mu=mu, weighting=a.weighting, seed=a.seed, n_lags=nl)
        gm = Forecaster(nf, a.target, a.seed, n_lags=nl); gm.set_params(glob)
        metrics = evaluate.score_scaled(te_df, gm.predict(Xte))
        extra["loss_history"] = [round(h, 5) for h in hist]
        if a.method == "selective":
            models, chosen = fed.train_selective(glob, cd, nf, a.target, a.ft_epochs or 3,
                                                 a.epochs, a.lr, seed=a.seed, n_lags=nl)
            metrics = evaluate.score_scaled(te_df, fed.predict_per_client(models, te_df, Xte, lag1=nl-1))
            from collections import Counter
            extra["selection_counts"] = dict(Counter(chosen.values()))
        elif a.ft_epochs > 0:
            pers = fed.personalise(glob, cd, nf, a.target, a.ft_epochs, a.lr, seed=a.seed, n_lags=nl)
            extra["ft_metrics"] = evaluate.score_scaled(
                te_df, fed.predict_per_client(pers, te_df, Xte, lag1=nl-1))

    name = a.method + (f"_mu{a.mu}" if a.method == "fedprox" else "") \
        + (f"_ft{a.ft_epochs}" if a.ft_epochs else "") + f"_{a.target}" \
        + (f"_w{a.weighting}" if a.method in ("fedavg", "fedprox") and a.weighting != "n" else "") \
        + (f"_win{a.window}" if a.window != 12 else "") + (f"_{a.tag}" if a.tag else "")
    rec = {"name": name, "config": vars(a), "metrics": metrics, **extra,
           "bar_R01": evaluate.naive_bar(te_df), "n_test_points": int(len(te_df)),
           "n_clients": len(cd), "seed": a.seed, "git": git_sha(),
           "duration_s": round(time.time() - t0, 1)}
    out = Path(a.out_dir) / f"{name}_s{a.seed}.json"
    out.write_text(json.dumps(rec, indent=2))
    print(f"{name} s{a.seed}: macro {metrics.get('macro_mean', float('nan')):.2f}% "
          f"median {metrics.get('median', float('nan')):.2f}%"
          + (f" | +ft macro {extra['ft_metrics']['macro_mean']:.2f}%" if "ft_metrics" in extra else "")
          + f" | {rec['duration_s']}s -> {out.name}")


if __name__ == "__main__":
    main()
