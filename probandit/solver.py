import os
import socket

import probcli.answerparser as answerparser
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
        self.base_solver = self.config.get('base_solver', '\'PROB\'')
        self.pred_call = self.config.get('pred_call', None)
        if self.pred_call is None:
            self.pred_call = f'cbc_timed_solve_with_opts({self.base_solver},_,$pred,_,Res,Msec)'

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


    def start(self, port=None, cli_args=[]):
        used_port = self.cli.start(port, cli_args)
        self.port = used_port


    def close(self):
        self.cli.close()
        self.port = None


    def solve(self, predicate):
        parsed_pred = self.cli.parser.parse_to_prolog(predicate)
        query = self.pred_call.replace('$pred', parsed_pred)

        self.cli.send_prolog(query)
        answer, info = self.cli.receive_prolog()

        if info and 'Res' in info:
            solution = info['Res']['value'][1][0]
            bindings = answerparser.translate_prolog_dot_list(solution)
            bindings = answerparser.translate_bindings(bindings)
            info = bindings

        return answer, info
