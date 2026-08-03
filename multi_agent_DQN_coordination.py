"""
Multi-Agent Deep Q-Network (DQN) Coordination (Fixed & Optimized)
4 agents in a 5x5 grid shuttle items from pickup (A) to drop-off (B) and back,
learning to coordinate and avoid head-on collisions using Deep Q-Networks.
"""

import os
import random
import time
from collections import deque
from enum import Enum

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

# Try importing IPython clear_output for Jupyter environments if available
try:
    from IPython.display import clear_output
    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False

# ============================================================================
# SEED SETUP
# ============================================================================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# ============================================================================
# CONSTANTS & HYPERPARAMETERS
# ============================================================================
GRID_SIZE = 5
NUM_AGENTS = 4

# Training Parameters
NUM_EPISODES = 2500
MAX_STEPS_PER_EPISODE = 50

# DQN Hyperparameters
LEARNING_RATE = 0.001
GAMMA = 0.99
BATCH_SIZE = 64
REPLAY_BUFFER_SIZE = 100_000
TARGET_UPDATE_FREQ = 500

EPSILON_START = 1.0
EPSILON_END = 0.01
EPSILON_DECAY = 0.9985

# Rewards & Penalties
STEP_REWARD = -0.5
PICKUP_REWARD = 15.0
DELIVERY_REWARD = 25.0
COLLISION_PENALTY = -25.0


# ============================================================================
# ENVIRONMENT: 5x5 GRID WITH 4 AGENTS
# ============================================================================
class Direction(Enum):
    NORTH = 0
    SOUTH = 1
    EAST  = 2
    WEST  = 3

MOVES = {
    Direction.NORTH: (-1, 0),
    Direction.SOUTH: (1, 0),
    Direction.EAST:  (0, 1),
    Direction.WEST:  (0, -1),
}


class MultiAgentGrid:
    """
    5x5 grid with 4 agents. A and B are randomly placed per episode.
    Agents start at A (empty), move to B (pickup automatically), then return to A.
    """
    def __init__(self):
        self.grid_size = GRID_SIZE
        self.num_agents = NUM_AGENTS
        self.agents = []      # each: {'row', 'col', 'has_item', 'delivered'}
        self.A = None         # (row, col) pickup
        self.B = None         # (row, col) drop-off
        self.step_count = 0
        self.collision_count = 0
        self.total_reward = 0.0

    def reset(self):
        """Place A and B randomly; all agents start at A with no item."""
        self.A = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
        self.B = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
        while self.A == self.B:
            self.B = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

        self.agents = []
        for _ in range(self.num_agents):
            self.agents.append({
                'row': self.A[0],
                'col': self.A[1],
                'has_item': False,
                'delivered': False
            })

        self.step_count = 0
        self.collision_count = 0
        self.total_reward = 0.0
        return self._get_state()

    def _get_state(self):
        """
        Observation for each agent i:
        - Self row, col (normalized)
        - Self has_item (0 or 1)
        - Landmark A row, col (normalized)
        - Landmark B row, col (normalized)
        - Other 3 agents' row, col (normalized)
        Total state dim = 13
        """
        states = []
        for i, ag in enumerate(self.agents):
            s = [
                ag['row'] / (GRID_SIZE - 1),
                ag['col'] / (GRID_SIZE - 1),
                1.0 if ag['has_item'] else 0.0,
                self.A[0] / (GRID_SIZE - 1),
                self.A[1] / (GRID_SIZE - 1),
                self.B[0] / (GRID_SIZE - 1),
                self.B[1] / (GRID_SIZE - 1),
            ]
            for j, other_ag in enumerate(self.agents):
                if i != j:
                    s.append(other_ag['row'] / (GRID_SIZE - 1))
                    s.append(other_ag['col'] / (GRID_SIZE - 1))
            states.append(np.array(s, dtype=np.float32))
        return states

    def get_state_dim(self):
        return 13

    def _detect_collisions(self, actions, old_positions):
        """
        Detect head-on collisions:
        - Multiple agents on same cell moving in different directions.
        - Swap collisions (agents exchange positions).
        Collisions at A or B are ignored.
        """
        collided = set()

        # 1) Same cell with different directions
        pos_map = {}
        for i, ag in enumerate(self.agents):
            pos = (ag['row'], ag['col'])
            pos_map.setdefault(pos, []).append(i)

        for pos, indices in pos_map.items():
            if pos == self.A or pos == self.B:
                continue
            if len(indices) > 1:
                dirs = [actions[i].value for i in indices]
                if len(set(dirs)) > 1:
                    collided.update(indices)

        # 2) Swap collisions
        for i in range(self.num_agents):
            for j in range(i + 1, self.num_agents):
                new_i = (self.agents[i]['row'], self.agents[i]['col'])
                new_j = (self.agents[j]['row'], self.agents[j]['col'])
                old_i = old_positions[i]
                old_j = old_positions[j]
                if new_i == old_j and new_j == old_i:
                    if (actions[i].value + actions[j].value) in [1, 5]:  # N+S, E+W
                        if old_i != self.A and old_i != self.B and old_j != self.A and old_j != self.B:
                            collided.add(i)
                            collided.add(j)

        return list(collided)

    def step(self, actions):
        """
        Execute all actions in random order (sequential).
        Returns: next_states, rewards, done
        """
        old_positions = [(ag['row'], ag['col']) for ag in self.agents]
        order = list(range(self.num_agents))
        random.shuffle(order)

        # Apply actions
        for idx in order:
            agent = self.agents[idx]
            dr, dc = MOVES[actions[idx]]
            agent['row'] = max(0, min(agent['row'] + dr, GRID_SIZE - 1))
            agent['col'] = max(0, min(agent['col'] + dc, GRID_SIZE - 1))

        # Detect collisions
        collided = self._detect_collisions(actions, old_positions)
        self.collision_count += len(collided)

        # Compute rewards with distance guidance
        rewards = []
        for i, ag in enumerate(self.agents):
            target = self.B if not ag['has_item'] and not ag['delivered'] else self.A
            old_r, old_c = old_positions[i]
            old_dist = abs(old_r - target[0]) + abs(old_c - target[1])
            new_dist = abs(ag['row'] - target[0]) + abs(ag['col'] - target[1])

            reward = STEP_REWARD + (old_dist - new_dist) * 1.5

            # Pickup at B
            if (ag['row'], ag['col']) == self.B and not ag['has_item'] and not ag['delivered']:
                ag['has_item'] = True
                reward += PICKUP_REWARD

            # Delivery at A
            if (ag['row'], ag['col']) == self.A and ag['has_item']:
                ag['has_item'] = False
                ag['delivered'] = True
                reward += DELIVERY_REWARD

            # Collision penalty
            if i in collided:
                reward += COLLISION_PENALTY

            rewards.append(reward)
            self.total_reward += reward

        self.step_count += 1
        all_returned = all(ag['delivered'] and (ag['row'], ag['col']) == self.A for ag in self.agents)
        done = all_returned or self.step_count >= MAX_STEPS_PER_EPISODE
        next_states = self._get_state()
        return next_states, rewards, done

    def render(self):
        """Draw the grid with A, B, and 4 agents (labelled 1-4)."""
        grid = [["⬜" for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        grid[self.A[0]][self.A[1]] = "🟩"  # A (pickup)
        grid[self.B[0]][self.B[1]] = "🟥"  # B (drop-off)

        for i, ag in enumerate(self.agents):
            r, c = ag['row'], ag['col']
            label = f"{i+1}"
            if ag['has_item']:
                grid[r][c] = f"📦{label}"
            else:
                grid[r][c] = f"🤖{label}"

        if HAS_IPYTHON:
            clear_output(wait=True)
        else:
            os.system("cls" if os.name == "nt" else "clear")

        for row in grid:
            print(" ".join(row))
        print(f"Step: {self.step_count}  |  Collisions: {self.collision_count}")
        print(f"A = {self.A}, B = {self.B}")


# ============================================================================
# DQN NETWORK & REPLAY BUFFER
# ============================================================================
class DQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim)
        )

    def forward(self, x):
        return self.net(x)


class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        s, a, r, ns, d = map(np.array, zip(*batch))
        return (torch.FloatTensor(s),
                torch.LongTensor(a),
                torch.FloatTensor(r),
                torch.FloatTensor(ns),
                torch.FloatTensor(d))

    def __len__(self):
        return len(self.buffer)


# ============================================================================
# TRAINING FUNCTION
# ============================================================================
def train():
    env = MultiAgentGrid()
    input_dim = env.get_state_dim()
    output_dim = len(Direction)

    q_net = DQN(input_dim, output_dim)
    target_net = DQN(input_dim, output_dim)
    target_net.load_state_dict(q_net.state_dict())
    target_net.eval()

    optimizer = optim.Adam(q_net.parameters(), lr=LEARNING_RATE)
    replay_buffer = ReplayBuffer(REPLAY_BUFFER_SIZE)

    epsilon = EPSILON_START
    step_count = 0
    collision_total = 0
    episode_rewards = []
    start_time = time.time()

    print("Training started...")
    print(f"Episodes budget: {NUM_EPISODES:,}, Max steps/ep: {MAX_STEPS_PER_EPISODE}")

    for episode in range(1, NUM_EPISODES + 1):
        states = env.reset()
        episode_reward = 0.0
        done = False

        while not done:
            actions = []
            for i in range(NUM_AGENTS):
                state_t = torch.FloatTensor(states[i]).unsqueeze(0)
                if random.random() < epsilon:
                    action = random.randint(0, output_dim - 1)
                else:
                    with torch.no_grad():
                        q_vals = q_net(state_t)
                        action = torch.argmax(q_vals, dim=1).item()
                actions.append(Direction(action))

            next_states, rewards, done = env.step(actions)

            for i in range(NUM_AGENTS):
                replay_buffer.push(states[i], actions[i].value, rewards[i], next_states[i], done)

            states = next_states
            episode_reward += sum(rewards)
            step_count += 1
            collision_total += env.collision_count

            # Train DQN every 2 environment steps
            if step_count % 2 == 0 and len(replay_buffer) >= BATCH_SIZE:
                batch = replay_buffer.sample(BATCH_SIZE)
                state_b, action_b, reward_b, next_state_b, done_b = batch

                q_values = q_net(state_b).gather(1, action_b.unsqueeze(1)).squeeze(1)
                with torch.no_grad():
                    next_q = target_net(next_state_b).max(1)[0]
                    target_q = reward_b + GAMMA * next_q * (1 - done_b)

                loss = nn.MSELoss()(q_values, target_q)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            # Update target network
            if step_count % TARGET_UPDATE_FREQ == 0:
                target_net.load_state_dict(q_net.state_dict())

        # Decay epsilon per episode
        epsilon = max(EPSILON_END, epsilon * EPSILON_DECAY)
        episode_rewards.append(episode_reward)

        if episode % 500 == 0:
            elapsed = time.time() - start_time
            print(f"Ep {episode:5d}/{NUM_EPISODES} | Steps {step_count:7d} | Collisions {collision_total:5d} | ε {epsilon:.3f} | Time {elapsed:.0f}s")

    elapsed = time.time() - start_time
    print("\n✅ Training completed.")
    print(f"Total Episodes: {NUM_EPISODES}")
    print(f"Total agent steps: {step_count:,}")
    print(f"Time elapsed: {elapsed:.2f}s")

    # Save training reward plot
    try:
        plt.figure(figsize=(10, 4))
        plt.plot(episode_rewards)
        plt.title("Training Episode Reward (Sum of All Agents)")
        plt.xlabel("Episode")
        plt.ylabel("Reward")
        plt.grid(True)
        plt.tight_layout()
        plot_path = "dqn_reward_plot.png"
        plt.savefig(plot_path)
        print(f"Saved reward plot to {plot_path}")
        plt.close()
    except Exception as e:
        print(f"Plot saving skipped: {e}")

    return q_net, env


# ============================================================================
# PERFORMANCE EVALUATION
# ============================================================================
def test_performance(q_net, num_scenarios=1000):
    env = MultiAgentGrid()
    successes = 0

    print(f"\nTesting on {num_scenarios} random scenarios...")

    for _ in range(num_scenarios):
        states = env.reset()
        steps_taken = 0
        collision_occurred = False

        while steps_taken < 25 and not collision_occurred:
            actions = []
            for i in range(NUM_AGENTS):
                state_t = torch.FloatTensor(states[i]).unsqueeze(0)
                with torch.no_grad():
                    q_vals = q_net(state_t)
                    action = torch.argmax(q_vals, dim=1).item()
                actions.append(Direction(action))

            next_states, rewards, _ = env.step(actions)
            steps_taken += 1

            if any(r <= COLLISION_PENALTY for r in rewards):
                collision_occurred = True
                break

            all_returned = all((ag['row'], ag['col']) == env.A and not ag['has_item'] for ag in env.agents)
            if all_returned and env.step_count > 1:
                successes += 1
                break

            states = next_states

    success_rate = (successes / num_scenarios) * 100
    print(f"Success rate: {success_rate:.2f}%")
    print("Requirement: > 75%")
    if success_rate >= 75.0:
        print("✅ Performance requirement MET.")
    else:
        print("❌ Performance requirement NOT MET.")
    return success_rate


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    print(f"PyTorch version: {torch.__version__}")
    print("Starting Multi-Agent DQN Coordination training & evaluation...")
    trained_qnet, trained_env = train()
    test_performance(trained_qnet)
