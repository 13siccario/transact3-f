"""Multi-task LSTM: one network predicts every target one step ahead from the last `seq_len` hours."""
from __future__ import annotations

import numpy as np


def fit_predict(Z: np.ndarray, target_cols: list[int], train_origins: np.ndarray, test_origins: np.ndarray,
                horizon: int, cfg: dict, seed: int, delta: np.ndarray | None = None) -> np.ndarray:
    """Z: (T, K) panel matrix. `delta` (bool per target) forecasts y[t+h] - y[t] instead of the level.

     Returns (len(test_origins), len(target_cols)) in original units.

    Scaling statistics come from training rows only. Origins earlier than seq_len are skipped by the caller.
    """
    import torch
    from torch import nn

    torch.set_num_threads(1)   # avoids an OpenMP clash with LightGBM that hangs on macOS
    torch.manual_seed(seed)
    L = cfg["seq_len"]
    last_train = train_origins.max() + horizon
    mu = Z[: last_train + 1].mean(0)
    sd = Z[: last_train + 1].std(0) + 1e-12
    Zs = (Z - mu) / sd

    def seqs(origins):
        return np.stack([Zs[o - L + 1: o + 1] for o in origins])

    Xtr = torch.tensor(seqs(train_origins), dtype=torch.float32)
    d = np.zeros(len(target_cols)) if delta is None else np.asarray(delta, dtype=float)
    Yraw = Z[train_origins + horizon][:, target_cols] - d * Z[train_origins][:, target_cols]
    ymu, ysd = Yraw.mean(0), Yraw.std(0) + 1e-12            # target scaling from training rows only
    Ytr = torch.tensor((Yraw - ymu) / ysd, dtype=torch.float32)
    Xte = torch.tensor(seqs(test_origins), dtype=torch.float32)

    class Net(nn.Module):
        def __init__(self, k_in, k_out, hidden):
            super().__init__()
            self.lstm = nn.LSTM(k_in, hidden, batch_first=True)
            self.head = nn.Linear(hidden, k_out)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1])

    net = Net(Z.shape[1], len(target_cols), cfg["hidden"])
    opt = torch.optim.Adam(net.parameters(), lr=cfg["lr"])
    g = torch.Generator().manual_seed(seed)
    for _ in range(cfg["epochs"]):
        perm = torch.randperm(len(Xtr), generator=g)
        for i in range(0, len(perm), cfg["batch_size"]):
            b = perm[i: i + cfg["batch_size"]]
            opt.zero_grad()
            nn.functional.mse_loss(net(Xtr[b]), Ytr[b]).backward()
            opt.step()
    net.eval()
    with torch.no_grad():
        pred = net(Xte).numpy()
    return pred * ysd + ymu + d * Z[test_origins][:, target_cols]
