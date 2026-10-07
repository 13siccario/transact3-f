"""Disjoint LinUCB over rails. Chooses a rail to send on now; learns from delayed settlement feedback."""
from __future__ import annotations

import numpy as np

from ..sim.env import K, OBS_DIM
from .rules import Policy


class LinUCB(Policy):
    learns = True

    def __init__(self, alpha: float = 0.4, ridge: float = 1.0, seed: int = 0):
        self.alpha, self.ridge = alpha, ridge
        self.name = "linucb"
        self.d = OBS_DIM + 1
        self.reset()

    def reset(self):
        self.A = [self.ridge * np.eye(self.d) for _ in range(K)]
        self.b = [np.zeros(self.d) for _ in range(K)]

    def _x(self, obs):
        return np.concatenate([[1.0], obs]).astype(float)

    def act(self, env, obs):
        x = self._x(obs)
        mask = env.send_mask()
        best, arm = -np.inf, None
        for i in np.flatnonzero(mask):
            Ainv = np.linalg.inv(self.A[i])
            theta = Ainv @ self.b[i]
            ucb = theta @ x + self.alpha * np.sqrt(x @ Ainv @ x)
            if ucb > best:
                best, arm = ucb, i
        return 1 + int(arm)

    def observe(self, obs, action, reward):
        if action == 0:
            return
        i, x = action - 1, self._x(obs)
        self.A[i] += np.outer(x, x)
        self.b[i] += reward * x
