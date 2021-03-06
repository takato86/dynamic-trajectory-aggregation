import numpy as np
import math
import logging
from .policy import SoftmaxPolicy, EgreedyPolicy
from .tabular import Tabular
from .reward_shaping import NaiveSubgoalRewardShaping,\
                            SubgoalSarsaRewardShaping,\
                            SarsaRewardShaping
import shaner
import csv

logger = logging.getLogger(__name__)


class SarsaAgent:
    def __init__(self, discount, epsilon, lr, nfeatures, nactions, temperature, rng, q_value={}):
        logger.debug("SarsaAgent is going to perform!")
        self.discount = discount
        self.epsilon = epsilon
        self.lr = lr
        self.nfeatures = nfeatures
        self.nactions = nactions
        self.temperature = temperature
        self.q_value = q_value
        self.policy = SoftmaxPolicy(rng, nfeatures, nactions, temperature)
        self.critic = Sarsa(discount, lr, self.policy.weights)
        self.features = Tabular(nfeatures)
        self.total_shaped_reward = 0
        for state, value in q_value.items():
            phi = self.features(state)
            self.critic.initialize(phi, value)

    def act(self, state):
        return self.policy.sample(self.features(state))
    
    def update(self, state, action, next_state, reward, done):
        phi = self.features(state)
        next_phi = self.features(next_state)
        next_action = self.act(next_state)
        _ = self.critic.update(phi, action, next_phi, reward, done, next_action)
    
    def reset(self):
        rng = np.random.RandomState(np.random.randint(0, 100))
        self.policy = SoftmaxPolicy(rng, self.nfeatures, self.nactions, self.temperature)
        self.critic = Sarsa(self.discount, self.lr, self.policy.weights)
        self.features = Tabular(self.nfeatures)
        self.total_shaped_reward = 0
        for state, value in self.q_value.items():
            phi = self.features(state)
            self.critic.initialize(phi, value)
    

class SubgoalRSSarsaAgent(SarsaAgent):
    def __init__(self, discount, epsilon, lr, nfeatures, nactions, temperature, rng, subgoals, eta, rho=0, subgoal_values=None):
        super().__init__(discount, epsilon, lr, nfeatures, nactions, temperature, rng)
        logger.debug("SubgoalRSSarsaAgent is going to perform!")
        self.subgoals = subgoals
        self.eta = eta
        self.rho = rho
        self.subgoal_values = subgoal_values
        self.reward_shaping = SubgoalSarsaRewardShaping(discount, eta, subgoals, nfeatures, discount, lr)
        
    def update(self, state, action, next_state, reward, done):
        phi = self.features(state)
        next_phi = self.features(next_state)
        self.reward_shaping.fit(next_state, reward, done)
        reward += self.reward_shaping.value(next_state, done)
        next_action = self.act(next_state)
        self.total_shaped_reward += reward
        _ = self.critic.update(phi, action, next_phi, reward, done, next_action)

    def reset(self):
        rng = np.random.RandomState(np.random.randint(0, 100))
        self.__init__(self.discount, self.epsilon, self.lr, self.nfeatures, self.nactions,
                      self.temperature, rng, self.subgoals, self.eta, self.rho, self.subgoal_values)

class NaiveSubgoalSarsaAgent(SubgoalRSSarsaAgent):
    def __init__(self, discount, epsilon, lr, nfeatures, nactions, temperature, rng, subgoals, eta, rho=0, subgoal_values=None):
        super().__init__(discount, epsilon, lr, nfeatures, nactions, temperature, rng, subgoals, eta, rho=0,
                         subgoal_values=subgoal_values)
        self.reward_shaping = NaiveSubgoalRewardShaping(discount, eta, subgoals, nfeatures)

class Sarsa:
    def __init__(self, discount, lr, weights):
        self.lr = lr
        self.discount = discount
        self.weights = weights

    def initialize(self, phi, q_value, action=None):
        if action is None:
            self.weights[phi, :] = q_value
        else:
            self.weights[phi, action] = q_value

    def value(self, phi, action=None):
        if action is None:
            return np.sum(self.weights[phi, :], axis=0)
        return np.sum(self.weights[phi, action], axis=0)

    def advantage(self, phi, action=None):
        values = self.value(phi)
        advantages = values - np.max(values)
        if action is None:
            return advantages
        return advantages[action]

    def update(self, phi, action, next_phi, reward, done, next_action):
        # One-step update target
        update_target = reward
        if not done:
            next_values = self.value(next_phi)
            update_target += self.discount * next_values[next_action]
        # Dense gradient update step
        tderror = update_target - self.value(phi, action)
        self.weights[phi, action] += self.lr * tderror
        return update_target


class SarsaRSSarsaAgent(SarsaAgent):
    def __init__(self, discount, epsilon, lr, nfeatures, nactions, temperature, rng, aggr_set):
        logger.debug("SarsaRSSarsaAgent is going to perform!")
        super().__init__(discount, epsilon, lr, nfeatures, nactions, temperature, rng)
        self.aggr_set = aggr_set
        self.reward_shaping = SarsaRewardShaping(discount, nfeatures, discount, lr, aggr_set)
        
    def update(self, state, action, next_state, reward, done):
        phi = self.features(state)
        next_phi = self.features(next_state)
        self.reward_shaping.fit(next_state, reward, done)
        reward += self.reward_shaping.value(next_state, done)
        next_action = self.act(next_state)
        self.total_shaped_reward += reward
        _ = self.critic.update(phi, action, next_phi, reward, done, next_action)

    def reset(self):
        rng = np.random.RandomState(np.random.randint(0, 100))
        self.__init__(self.discount, self.epsilon, self.lr, self.nfeatures, self.nactions,
                      self.temperature, rng, self.aggr_set)

class SRSSarsaAgent(SarsaAgent):
    def __init__(self, discount, epsilon, lr, env, temperature, rng, eta, rho, subgoals):
        nfeatures = env.observation_space.n
        nactions = env.action_space.n
        super().__init__(discount, epsilon, lr, nfeatures, nactions, temperature, rng)
        params = {
            'vid': 'table',
            'aggr_id': 'dta',
            'eta': eta,
            'rho': rho,
            'params': {
                'env_id': env.spec.id,
                '_range': 0,
                'n_obs': nfeatures,
                'subgoals': subgoals
            }
        }
        self.reward_shaping = shaner.SubgoalRS(lr, discount, env, params)
    
    def update(self, state, action, next_state, reward, done):
        F = self.reward_shaping.perform(state, next_state, reward, done)
        super().update(state, action, next_state, reward + F, done)
    
    def reset(self):
        super().reset()
        self.reward_shaping.reset()
