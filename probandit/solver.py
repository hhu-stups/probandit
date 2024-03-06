import os
import socket

from probcli import ProBCli

class Solver():

    def __init__(self, **solver_config):
        """
        Create a new Solver object. The configuration is a dictionary with
        the following keys (also see the solver configuration section in the
        README.md):

        - path (mandatory): the path to the solver binary
        - base_solver (optional): the base solver to use
            - one of 'PROB', 'KODKOD', 'Z3', 'Z3AXM', 'Z3CNS', 'CDCLT'
            - Default is 'PROB'
        - preferences (optional): a list of ProBCli preferences
        """
        self.config = solver_config

        self.path = os.path.expandvars(self.config['path'])
        # Check if the path is a file or a directory
        if not os.path.exists(self.path):
            raise ValueError(f"Path {self.path} does not exist")
        if os.path.isdir(self.path):
            self.path = os.path.join(self.path, 'probcli')

        self.preferences = self.config.get('preferences', [])
        self.base_solver = self.config.get('base_solver', 'PROB')
        self.pred_call = self.config.get('pred_call', None)
        if self.pred_call is not None:
            self.pred_call = f'cbc_timed_solve_with_opts({self.base_solver},Options,Predicate,Identifiers,Result,Milliseconds)'

        self._cli_args = []
        for pref in self.preferences:
            # Prefs can be strings or dicts
            if isinstance(pref, dict):
                for k, v in pref.items():
                    if isinstance(v, bool):
                        v = 'TRUE' if v else 'FALSE'
                    self._cli_args += ['-p', k, v]
            else:
                self._cli_args += ['-p'] + pref.split()

        self.cli = ProBCli(self.path)


    def start(self, port=None):
        call_args = [self.path]
        used_port = self.cli.start(port, call_args)
        self.port = used_port


    def connect_socket(self, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
