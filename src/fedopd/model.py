"""fedOPD forecaster: MLP 33->64->32->1 behind get_params/set_params/train_epochs/predict.

The federated loop touches ONLY this interface, so the model is swappable without touching
federation (CLAUDE.md §7). Two target formulations (D-08, decided at Step 5):
  level: predict scaled demand y_s(t).
  delta: predict y_s(t) - y_s(t-1); reconstruct as lag1 + prediction. Naive-anchored -- a model
         predicting zero delta reproduces naive t-1 exactly, so it starts at the bar (F-27).
"""
from __future__ import annotations
import numpy as np
import torch
import torch.nn as nn

torch.set_num_threads(2)   # OPS: cap threads; parallelise across configs, not within a run

LAG1_COL = 11              # index of the most recent scaled lag in the 33-feature layout


def _seed(seed: int):
    torch.manual_seed(seed)
    np.random.seed(seed)


class Forecaster:
    def __init__(self, n_features: int = 33, target: str = "level", seed: int = 0,
                 weight_decay: float = 1e-4):
        assert target in ("level", "delta")
        self.target, self.n_features, self.seed = target, n_features, seed
        _seed(seed)
        self.net = nn.Sequential(nn.Linear(n_features, 64), nn.ReLU(),
                                 nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))
        self.weight_decay = weight_decay

    # ---- the interface the FL loop is allowed to touch -------------------------------
    def get_params(self) -> list[np.ndarray]:
        return [p.detach().cpu().numpy().copy() for p in self.net.parameters()]

    def set_params(self, params: list[np.ndarray]):
        with torch.no_grad():
            for p, w in zip(self.net.parameters(), params):
                p.copy_(torch.from_numpy(np.asarray(w, np.float32)))

    def train_epochs(self, X, y, epochs=1, lr=1e-3, batch=64, mu=0.0, global_params=None,
                     val=None, patience=5):
        """SGD over (X, y). mu>0 adds the FedProx proximal term ||w - w_global||^2 * mu/2.
        val=(Xv, yv) enables early stopping on val MSE with the given patience (fair-fight
        local-only, H1). Returns the final train loss."""
        X = torch.from_numpy(np.asarray(X, np.float32))
        t = torch.from_numpy(self._target(np.asarray(X), np.asarray(y, np.float32)))
        opt = torch.optim.Adam(self.net.parameters(), lr=lr, weight_decay=self.weight_decay)
        gref = ([torch.from_numpy(np.asarray(w, np.float32)) for w in global_params]
                if (mu > 0 and global_params is not None) else None)
        g = torch.Generator().manual_seed(self.seed)
        best, best_state, wait, loss = np.inf, None, 0, torch.tensor(0.0)
        for _ in range(epochs):
            for idx in torch.randperm(len(X), generator=g).split(batch):
                opt.zero_grad()
                loss = nn.functional.mse_loss(self.net(X[idx]).squeeze(-1), t[idx])
                if gref is not None:
                    loss = loss + (mu / 2) * sum(((p - w) ** 2).sum()
                                                 for p, w in zip(self.net.parameters(), gref))
                loss.backward(); opt.step()
                loss = loss.detach()
            if val is not None:
                v = self._val_mse(*val)
                if v < best - 1e-6:
                    best, wait = v, 0
                    best_state = [p.detach().clone() for p in self.net.parameters()]
                else:
                    wait += 1
                    if wait >= patience:
                        break
        if val is not None and best_state is not None:
            with torch.no_grad():
                for p, w in zip(self.net.parameters(), best_state):
                    p.copy_(w)
        return float(loss)

    def predict(self, X) -> np.ndarray:
        """Scaled-level predictions (delta models reconstruct level = lag1 + delta)."""
        X = np.asarray(X, np.float32)
        with torch.no_grad():
            out = self.net(torch.from_numpy(X)).squeeze(-1).numpy()
        return X[:, LAG1_COL] + out if self.target == "delta" else out

    # ---- internals --------------------------------------------------------------------
    def _target(self, X, y):
        return (y - X[:, LAG1_COL]).astype(np.float32) if self.target == "delta" else y

    def _val_mse(self, Xv, yv):
        Xv = np.asarray(Xv, np.float32)
        with torch.no_grad():
            out = self.net(torch.from_numpy(Xv)).squeeze(-1).numpy()
        t = self._target(Xv, np.asarray(yv, np.float32))
        return float(np.mean((out - t) ** 2))


def clone_with(params, n_features=33, target="level", seed=0) -> Forecaster:
    m = Forecaster(n_features, target, seed)
    m.set_params(params)
    return m
