"""Step 9 · Flower parity: the SAME model + data run under Flower's abstractions.

Clients are flwr.client.NumPyClient wrappers around our Forecaster; aggregation is
flwr.server.strategy.FedAvg.aggregate_fit — Flower's own implementation of the FL math.
Ray is not installed on this box, so the transport is an in-process driver loop rather
than flwr.simulation (caveat logged in BUILD_LOG); the science (client fit + strategy
aggregation) is Flower's code end to end.

Gate: |flower sMAPE - handwritten R-05 sMAPE| <= 0.3 at the same seed.
"""
import json, os, sys, time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import flwr
from flwr.client import NumPyClient
from flwr.common import (FitRes, Status, Code, ndarrays_to_parameters,
                         parameters_to_ndarrays)
from flwr.server.strategy import FedAvg

from src.fedopd import data, evaluate
from src.fedopd.model import Forecaster, clone_with

SEED, ROUNDS, LOCAL_EPOCHS, LR, TARGET = 0, 40, 1, 1e-3, "delta"


class TrustClient(NumPyClient):
    """One NHS trust as a Flower client, backed by the same Forecaster interface."""

    def __init__(self, cid, X, y, n_features, n_lags):
        self.cid, self.X, self.y = cid, X, y
        self.n_features, self.n_lags = n_features, n_lags

    def fit(self, parameters, config):
        m = clone_with(parameters, self.n_features, TARGET, SEED, n_lags=self.n_lags)
        m.train_epochs(self.X, self.y, epochs=LOCAL_EPOCHS, lr=LR, batch=64)
        return m.get_params(), len(self.y), {}


class _Proxy:                      # minimal ClientProxy stand-in for aggregate_fit
    def __init__(self, cid):
        self.cid = cid


def main():
    t0 = time.time()
    ds = data.build_all()
    cd = data.per_client(ds)
    nf, nl = ds["n_features"], ds["n_lags"]
    clients = {c: TrustClient(c, X, y, nf, nl) for c, (X, y) in sorted(cd.items())}
    strategy = FedAvg()            # Flower's aggregation (num_examples-weighted)

    glob = Forecaster(nf, TARGET, SEED, n_lags=nl).get_params()
    for rnd in range(1, ROUNDS + 1):
        results = []
        for cid, cl in clients.items():
            params, n, _ = cl.fit([w.copy() for w in glob], {})
            results.append((_Proxy(cid),
                            FitRes(status=Status(Code.OK, "ok"),
                                   parameters=ndarrays_to_parameters(params),
                                   num_examples=n, metrics={})))
        agg, _ = strategy.aggregate_fit(rnd, results, [])
        glob = parameters_to_ndarrays(agg)

    gm = Forecaster(nf, TARGET, SEED, n_lags=nl)
    gm.set_params(glob)
    metrics = evaluate.score_scaled(ds["te_df"], gm.predict(ds["Xte"]))

    ref = json.loads((data.ROOT / "results" / "fedavg_ft3_delta_s0.json").read_text())["metrics"]
    gap = abs(metrics["macro_mean"] - ref["macro_mean"])
    rec = {"name": "flower_fedavg_delta", "flwr_version": flwr.__version__,
           "metrics": metrics, "handwritten_R05": ref, "gap_macro": round(gap, 3),
           "gate": "PASS" if gap <= 0.3 else "FAIL", "seed": SEED,
           "caveat": "in-process driver (Ray not installed); client fit + FedAvg.aggregate_fit are Flower code",
           "duration_s": round(time.time() - t0, 1)}
    (data.ROOT / "results" / "flower_parity_s0.json").write_text(json.dumps(rec, indent=2))
    print(f"flower  macro {metrics['macro_mean']:.2f}% median {metrics['median']:.2f}% | "
          f"handwritten {ref['macro_mean']:.2f}% | gap {gap:.3f} -> GATE {rec['gate']}")


if __name__ == "__main__":
    main()
