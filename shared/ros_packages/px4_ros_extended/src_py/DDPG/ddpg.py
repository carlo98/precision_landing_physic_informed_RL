from __future__ import division
import os
import numpy as np
import torch
import torch.nn.functional as F

import DDPG.utils as utils
from DDPG.models import Critic_paper, Critic_small
from DDPG.models import Actor_paper, Actor_small_sep_head, Actor_small_one_head


class DDPG:
    def __init__(self, state_dim, action_dim, ram, model, lr_actor=0.0001, lr_critic=0.001, gamma=0.99, tau=0.001,
                 batch_size=128, epochs=3):
        """
        :param state_dim: Dimensions of state (int)
        :param action_dim: Dimension of action (int)
        :param ram: replay memory buffer object
        :return:
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.ram = ram
        self.iter = 0
        self.noise = utils.OrnsteinUhlenbeckActionNoise(self.action_dim)

        if model == "paper":
            actor = Actor_paper
            critic = Critic_paper
        elif model == "small":
            actor = Actor_small_sep_head
            critic = Critic_small
        elif model == "small_one_head":
            actor = Actor_small_one_head
            critic = Critic_small

        self.actor = actor(self.state_dim, self.action_dim).float()
        self.target_actor = actor(self.state_dim, self.action_dim).float()
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr_actor)

        self.critic = critic(self.state_dim, self.action_dim).float()
        self.target_critic = critic(self.state_dim, self.action_dim).float()
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr_critic)

        utils.hard_update(self.target_actor, self.actor)
        utils.hard_update(self.target_critic, self.critic)

        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        self.epochs = epochs
        
        self.path_models = "/src/shared/models"
        if not os.path.isdir(self.path_models):
            os.mkdir(self.path_models)

    def get_exploitation_action(self, state):
        """
        gets the action from target actor added with exploration noise
        :param state: state (Numpy array)
        :return: sampled action (Numpy array)
        """
        state = torch.from_numpy(state.reshape(-1, self.state_dim)).float()
        action = self.target_actor.forward(state).detach()
        return action.numpy()

    def get_exploration_action(self, state, n_steps):
        """
        gets the action from actor added with exploration noise
        :param state: state (Numpy array)
        :param n_steps: number of training steps, used to decrease exploration
        :return: sampled action (Numpy array)
        """
        state = torch.from_numpy(state.reshape(-1, self.state_dim)).float()
        action = self.actor.forward(state).detach()
        new_action = action.numpy() + self.noise.sample(n_steps)
        return np.clip(new_action, -1.0, 1.0)

    def optimize(self, mem_to_use):
        """
        Samples a random batch from replay memory and performs optimization
        :return:
        """
        for j in range(self.epochs):
            tot_loss_critic = 0.0
            tot_loss_actor = 0.0
            for s1, a1, r1, s2, done in self.ram.sample(mem_to_use, self.batch_size):
                self.actor_optimizer.zero_grad(set_to_none=True)
                self.critic_optimizer.zero_grad(set_to_none=True)

                # ---------------------- optimize critic ----------------------
                # Use target actor exploitation policy here for loss evaluation
                with torch.no_grad():
                    a2 = self.target_actor(s2).detach()
                    next_val = torch.squeeze(self.target_critic(s2, a2).detach())
                    # y_exp = r + gamma*Q'( s2, pi'(s2))
                    y_expected = r1 + (1-done) * self.gamma * next_val
                # y_pred = Q( s1, a1)
                y_predicted = torch.squeeze(self.critic(s1, a1))
                # compute critic loss, and update the critic
                loss_critic = F.smooth_l1_loss(y_predicted, y_expected)
                loss_critic.backward()
                self.critic_optimizer.step()

                # ---------------------- optimize actor ----------------------
                pred_a1 = self.actor(s1)
                loss_actor = -1*torch.mean(self.critic(s1, pred_a1))
                loss_actor.backward()
                self.actor_optimizer.step()

                tot_loss_critic += loss_critic.detach().numpy()
                tot_loss_actor += loss_actor.detach().numpy()

            print("Epoch: " + str(j) + " Loss Critic: " + str(tot_loss_critic) + " Loss Actor: "
                + str(tot_loss_actor))

        utils.soft_update(self.target_actor, self.actor, self.tau)
        utils.soft_update(self.target_critic, self.critic, self.tau)


    def save_models(self, id, best=False):
        """
        saves the target actor and critic models
        :param id: id of session
        :param best: if true saving best model, if false most recent one
        :return:
        """
        if best:
            base_path = self.path_models + '/' + str(id) + "_best"
        else:
            base_path = self.path_models + '/' + str(id)
        torch.save(self.target_actor.state_dict(), base_path + '_actor.pt')
        torch.save(self.target_critic.state_dict(), base_path + '_critic.pt')
        print('Models saved successfully')

    def load_models(self, id, best=True):
        """
        loads the target actor and critic models, and copies them onto actor and critic models
        :param id: id of session
        :param best: if true loading best model, if false last one
        :return:
        """
        if best:
            base_path = self.path_models + '/' + str(id) + "_best"
        else:
            base_path = self.path_models + '/' + str(id)
        self.actor.load_state_dict(torch.load(base_path + '_actor.pt'))
        self.critic.load_state_dict(torch.load(base_path + '_critic.pt'))
        utils.hard_update(self.target_actor, self.actor)
        utils.hard_update(self.target_critic, self.critic)
        print('Models loaded successfully')
