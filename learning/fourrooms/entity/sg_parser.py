import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--discount', help='Discount factor', type=float, default=0.99)
parser.add_argument('--lr_critic', help="Learning rate", type=float, default=1e-2)
parser.add_argument('--epsilon', help="Epsilon-greedy for policy over options", type=float, default=1e-2)
parser.add_argument('--nepisodes', help="Number of episodes per run", type=int, default=250)
parser.add_argument('--nruns', help="Number of runs", type=int, default=100)
parser.add_argument('--nsteps', help="Maximum number of steps per episode", type=int, default=1000)
parser.add_argument('--temperature', help="Temperature parameter for softmax", type=float, default=1e-2)
parser.add_argument('--mean_option_dur', default=4, type=int)
parser.add_argument('--env_id', default="Fourrooms-v0", type=str)
parser.add_argument('--subgoal-path', default="in/subgoals/fourrooms_subgoals.csv", type=str, help="Subgoal file path")
parser.add_argument('--eta', default=1, type=float, help="Intrinsic reward sizing")