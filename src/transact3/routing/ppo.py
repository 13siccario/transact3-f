"""PPO with hard action masking (sb3-contrib MaskablePPO). The mask carries the compliance filter,
so the network can never select an ineligible rail."""
from __future__ import annotations

import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from ..sim.env import RoutingEnv
from .rules import Policy


def train_ppo(env: RoutingEnv, timesteps: int, seed: int = 0) -> MaskablePPO:
    import torch
    torch.set_num_threads(1)
    masked = ActionMasker(env, lambda e: e.unwrapped.action_masks())
    model = MaskablePPO("MlpPolicy", masked, seed=seed, verbose=0, n_steps=512, batch_size=128,
                        learning_rate=3e-4, gamma=1.0, ent_coef=0.01, policy_kwargs={"net_arch": [64, 64]})
    model.learn(total_timesteps=timesteps)
    return model


class PPOPolicy(Policy):
    name = "ppo"

    def __init__(self, model: MaskablePPO):
        self.model = model

    def act(self, env, obs):
        a, _ = self.model.predict(obs, action_masks=env.action_masks(), deterministic=True)
        return int(a)
