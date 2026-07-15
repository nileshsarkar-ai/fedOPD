"""Hand-written federated loop (the scientific instrument): FedAvg / FedProx + personalisation.

Touches ONLY the Forecaster interface (get_params/set_params/train_epochs/predict), so the
model is swappable. Cross-silo, full participation: every client trains E local epochs per
round; the server aggregates with the chosen weighting.
"""
from __future__ import annotations
import numpy as np
from .model import Forecaster, clone_with


def _weights(clients, sizes, weighting):
    if weighting == "equal":
        w = np.ones(len(clients))
    elif weighting == "sqrt":
        w = np.sqrt(np.array([sizes[c] for c in clients], float))
    else:                                    # "n" -- classic FedAvg example-count weighting
        w = np.array([sizes[c] for c in clients], float)
    return w / w.sum()


def _tail_split(X, y, tail=12):
    """Last `tail` samples as validation (windows are built in time order per series, so the
    tail is the most recent slice -- a train-tail early-stopping split, not a random one)."""
    if len(X) <= tail * 2:
        return (X, y), None
    return (X[:-tail], y[:-tail]), (X[-tail:], y[-tail:])


def run_federated(client_data, n_features, target="level", rounds=40, local_epochs=1,
                  lr=1e-3, batch=64, mu=0.0, weighting="n", seed=0, log_every=10, verbose=False,
                  n_lags=12):
    """FedAvg (mu=0) / FedProx (mu>0). Returns (global_params, history)."""
    clients = sorted(client_data)
    sizes = {c: len(client_data[c][1]) for c in clients}
    w = _weights(clients, sizes, weighting)
    glob = Forecaster(n_features, target, seed, n_lags=n_lags).get_params()
    history = []
    for r in range(rounds):
        updates, losses = [], []
        for c in clients:
            m = clone_with(glob, n_features, target, seed, n_lags=n_lags)
            X, y = client_data[c]
            losses.append(m.train_epochs(X, y, epochs=local_epochs, lr=lr, batch=batch,
                                         mu=mu, global_params=glob))
            updates.append(m.get_params())
        glob = [np.sum([w[i] * u[k] for i, u in enumerate(updates)], axis=0)
                for k in range(len(glob))]
        history.append(float(np.mean(losses)))
        if verbose and (r + 1) % log_every == 0:
            print(f"  round {r+1}/{rounds}  mean local loss {history[-1]:.4f}")
    return glob, history


def personalise(global_params, client_data, n_features, target="level", ft_epochs=3,
                lr=1e-3, batch=64, seed=0, n_lags=12):
    """Fine-tune the final global model per client. Thin-client guard (H1 corollary): early
    stopping on a train-tail split caps effective epochs, so small clients are not overfitted
    right back by personalisation."""
    out = {}
    for c, (X, y) in client_data.items():
        m = clone_with(global_params, n_features, target, seed, n_lags=n_lags)
        (Xt, yt), val = _tail_split(X, y)
        m.train_epochs(Xt, yt, epochs=ft_epochs, lr=lr, batch=batch, val=val, patience=2)
        out[c] = m
    return out


def train_local_only(client_data, n_features, target="level", epochs=40, lr=1e-3,
                     batch=64, seed=0, n_lags=12):
    """Local-only baseline, compute-matched (epochs = rounds x local_epochs) and given a FAIR
    FIGHT (H1): early stopping on a train-tail split + weight decay + small-client batch."""
    out = {}
    for c, (X, y) in client_data.items():
        m = Forecaster(n_features, target, seed, n_lags=n_lags)
        (Xt, yt), val = _tail_split(X, y)
        b = int(min(batch, max(8, len(yt) // 4)))
        m.train_epochs(Xt, yt, epochs=epochs, lr=lr, batch=b, val=val, patience=5)
        out[c] = m
    return out


def train_centralised(Xtr, ytr, n_features, target="level", epochs=40, lr=1e-3,
                      batch=256, seed=0, n_lags=12):
    """All data pooled: the privacy-ignoring upper bound."""
    m = Forecaster(n_features, target, seed, n_lags=n_lags)
    m.train_epochs(Xtr, ytr, epochs=epochs, lr=lr, batch=batch)
    return m


def predict_per_client(models, te_df, Xte, lag1=11):
    """Route each test row to its owning trust's model; returns scaled predictions.
    A model of None means 'use naive t-1' for that client (the scaled lag-1 column)."""
    pred = np.empty(len(Xte), np.float32)
    for c, m in models.items():
        idx = np.flatnonzero((te_df.branch == c).values)
        if len(idx):
            pred[idx] = Xte[idx, lag1] if m is None else m.predict(Xte[idx])
    return pred


def train_selective(global_params, client_data, n_features, target="delta", ft_epochs=3,
                    local_epochs=40, lr=1e-3, seed=0, n_lags=12, sel=12):
    """Per-client model selection (the H1-refutation remedy): for each client choose the best of
    {naive t-1, local-only, global+fine-tune} by MSE on a held-out SELECTION slice (the last `sel`
    train windows, excluded from every candidate's fit), then REFIT the winner on the full train.
    Selection uses only training data -- no test peeking. Returns (models, chosen)."""
    lag1 = n_lags - 1
    models, chosen = {}, {}
    for c, (X, y) in client_data.items():
        if len(X) <= sel + MIN_FIT:                          # too small to select -> global+ft on all
            m = clone_with(global_params, n_features, target, seed, n_lags=n_lags)
            m.train_epochs(X, y, epochs=ft_epochs, lr=lr); models[c] = m; chosen[c] = "global+ft(small)"
            continue
        Xf, yf, Xv, yv = X[:-sel], y[:-sel], X[-sel:], y[-sel:]
        loc = Forecaster(n_features, target, seed, n_lags=n_lags); loc.train_epochs(Xf, yf, local_epochs, lr)
        ft = clone_with(global_params, n_features, target, seed, n_lags=n_lags); ft.train_epochs(Xf, yf, ft_epochs, lr)
        mse = {"naive": float(np.mean((Xv[:, lag1] - yv) ** 2)),
               "local": float(np.mean((loc.predict(Xv) - yv) ** 2)),
               "global+ft": float(np.mean((ft.predict(Xv) - yv) ** 2))}
        pick = min(mse, key=mse.get); chosen[c] = pick
        if pick == "naive":
            models[c] = None
        elif pick == "local":
            m = Forecaster(n_features, target, seed, n_lags=n_lags); m.train_epochs(X, y, local_epochs, lr); models[c] = m
        else:
            m = clone_with(global_params, n_features, target, seed, n_lags=n_lags); m.train_epochs(X, y, ft_epochs, lr); models[c] = m
    return models, chosen


MIN_FIT = 24
