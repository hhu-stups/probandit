import yaml
import sys

from probandit.solver import Solver

if __name__ == '__main__':
    # First argument is the config file path
    if len(sys.argv) < 2:
        print("Usage: python probandit.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]
    config = yaml.safe_load(open(config_file, 'r'))

    for id in config['solvers']:
        solver = Solver(**(config['solvers'][id]))
        print(solver._cli_args)