import numpy as np


class BfAgent:

    def __init__(self, actions: list) -> None:
        """
        Parameters
        ----------
        actions: List of action names.
        """
        self.actions = actions
        self.agents = {}

        for action in actions:
            self.agents[action] = ThompsonSampling()

    def sample_action(self):
        """
        Returns
        -------
        action: Name of the action to play.
        """
        samplings = [self.agents[agent].sample() for agent in self.agents]
        action = self.actions[np.argmax(samplings)]

        return action

    def receive_reward(self, last_action, reward):
        """
        Parameters
        ----------
        last_action: Id of the last action played which caused the reward.
        reward: 0 or 1
        """
        self.agents[last_action].receive_reward(reward)

    def get_actions(self):
        return self.actions

    def get_agent(self, action):
        return self.agents[action]


class ThompsonSampling:

    def __init__(self, decay=0.95) -> None:
        self.a = 0
        self.b = 0
        self.decay = decay
        self.rng = np.random.default_rng()

    def get_ab(self):
        return (self.a+1, self.b+1)

    def receive_reward(self, reward):
        if reward == 0:
            self.a = reward + self.decay * self.a
            self.b = 1 + self.decay * self.b
        elif reward == 1:
            self.a = 1 + self.decay * self.a
            self.b = self.decay * self.b
        else:
            raise AttributeError(
                "Reward for thompson sampling must be 0 or 1.")

    def sample(self) -> float:
        return self.rng.beta(self.a + 1, self.b + 1, size=1)
