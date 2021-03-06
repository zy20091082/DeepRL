#######################################################################
# Copyright (C) 2017 Shangtong Zhang(zhangshangtong.cpp@gmail.com)    #
# Permission given to modify the code as long as you keep this        #
# declaration at the top                                              #
#######################################################################

from .base_network import *

class DeterministicActorNet(nn.Module, BasicNet):
    def __init__(self,
                 state_dim,
                 action_dim,
                 action_gate=F.tanh,
                 action_scale=1,
                 gpu=-1,
                 non_linear=F.tanh):
        super(DeterministicActorNet, self).__init__()
        self.layer1 = nn.Linear(state_dim, 300)
        self.layer2 = nn.Linear(300, 200)
        self.layer3 = nn.Linear(200, action_dim)
        self.action_gate = action_gate
        self.action_scale = action_scale
        self.non_linear = non_linear
        self.init_weights()
        BasicNet.__init__(self, gpu)

    def init_weights(self):
        bound = 3e-3
        nn.init.uniform(self.layer3.weight.data, -bound, bound)
        nn.init.constant(self.layer3.bias.data, 0)

        nn.init.xavier_uniform(self.layer1.weight.data)
        nn.init.constant(self.layer1.bias.data, 0)
        nn.init.xavier_uniform(self.layer2.weight.data)
        nn.init.constant(self.layer2.bias.data, 0)

    def forward(self, x):
        x = self.variable(x)
        x = self.non_linear(self.layer1(x))
        x = self.non_linear(self.layer2(x))
        x = self.layer3(x)
        x = self.action_scale * self.action_gate(x)
        return x

    def predict(self, x, to_numpy=False):
        y = self.forward(x)
        if to_numpy:
            y = y.cpu().data.numpy()
        return y

class DeterministicCriticNet(nn.Module, BasicNet):
    def __init__(self,
                 state_dim,
                 action_dim,
                 gpu=-1,
                 non_linear=F.tanh):
        super(DeterministicCriticNet, self).__init__()
        self.layer1 = nn.Linear(state_dim, 400)
        self.layer2 = nn.Linear(400 + action_dim, 300)
        self.layer3 = nn.Linear(300, 1)
        self.non_linear = non_linear
        self.init_weights()
        BasicNet.__init__(self, gpu)

    def init_weights(self):
        bound = 3e-3
        nn.init.uniform(self.layer3.weight.data, -bound, bound)
        nn.init.constant(self.layer3.bias.data, 0)

        nn.init.xavier_uniform(self.layer1.weight.data)
        nn.init.constant(self.layer1.bias.data, 0)
        nn.init.xavier_uniform(self.layer2.weight.data)
        nn.init.constant(self.layer2.bias.data, 0)

    def forward(self, x, action):
        x = self.variable(x)
        action = self.variable(action)
        x = self.non_linear(self.layer1(x))
        x = self.non_linear(self.layer2(torch.cat([x, action], dim=1)))
        x = self.layer3(x)
        return x

    def predict(self, x, action):
        return self.forward(x, action)

class GaussianActorNet(nn.Module, BasicNet):
    def __init__(self,
                 state_dim,
                 action_dim,
                 gpu=-1,
                 hidden_size=64,
                 non_linear=F.tanh):
        super(GaussianActorNet, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc_action = nn.Linear(hidden_size, action_dim)

        self.action_log_std = nn.Parameter(torch.zeros(1, action_dim))

        self.non_linear = non_linear

        self.init_weights()
        BasicNet.__init__(self, gpu)

    def init_weights(self):
        bound = 3e-3
        nn.init.uniform(self.fc_action.weight.data, -bound, bound)
        nn.init.constant(self.fc_action.bias.data, 0)

        nn.init.orthogonal(self.fc1.weight.data)
        nn.init.constant(self.fc1.bias.data, 0)
        nn.init.orthogonal(self.fc2.weight.data)
        nn.init.constant(self.fc2.bias.data, 0)

    def forward(self, x):
        x = self.variable(x)
        phi = self.non_linear(self.fc1(x))
        phi = self.non_linear(self.fc2(phi))
        mean = F.tanh(self.fc_action(phi))
        log_std = self.action_log_std.expand_as(mean)
        std = log_std.exp()
        return mean, std, log_std

    def predict(self, x):
        return self.forward(x)

class GaussianCriticNet(nn.Module, BasicNet):
    def __init__(self,
                 state_dim,
                 gpu=-1,
                 hidden_size=64,
                 non_linear=F.tanh):
        super(GaussianCriticNet, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc_value = nn.Linear(hidden_size, 1)
        self.non_linear = non_linear
        self.init_weights()
        BasicNet.__init__(self, gpu)

    def init_weights(self):
        bound = 3e-3
        nn.init.uniform(self.fc_value.weight.data, -bound, bound)
        nn.init.constant(self.fc_value.bias.data, 0)

        nn.init.orthogonal(self.fc1.weight.data)
        nn.init.constant(self.fc1.bias.data, 0)
        nn.init.orthogonal(self.fc2.weight.data)
        nn.init.constant(self.fc2.bias.data, 0)

    def forward(self, x):
        x = self.variable(x)
        phi = self.non_linear(self.fc1(x))
        phi = self.non_linear(self.fc2(phi))
        value = self.fc_value(phi)
        return value

    def predict(self, x):
        return self.forward(x)

class DisjointActorCriticNet:
    def __init__(self, state_dim, action_dim, actor_network_fn, critic_network_fn):
        self.actor = actor_network_fn(state_dim, action_dim)
        self.critic = critic_network_fn(state_dim, action_dim)

    def state_dict(self):
        return [self.actor.state_dict(), self.critic.state_dict()]

    def load_state_dict(self, state_dicts):
        self.actor.load_state_dict(state_dicts[0])
        self.critic.load_state_dict(state_dicts[1])

    def parameters(self):
        return list(self.actor.parameters()) + list(self.critic.parameters())

    def zero_grad(self):
        self.actor.zero_grad()
        self.critic.zero_grad()
