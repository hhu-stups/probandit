import os
import socket

import probcli.answerparser as answerparser
from probcli import ProBCli

class Solver():

    def __init__(self, path, **solver_config):
        """
        Create a new Solver object. The configuration is a dictionary with
        the following keys (also see the solver configuration section in the
        README.md):

        - path (mandatory): the path to the solver binary
        - base_solver (optional): the base solver to use
            - one of 'PROB', 'KODKOD', 'Z3', 'Z3AXM', 'Z3CNS', 'CDCLT'
            - Default is 'PROB'
        - preferences (optional): a list of ProBCli preferences
        - pred_call (optional): the Prolog call used to evaluate a predicate.
            - Use $pred as a placeholder for the predicate
            - Default is 'prob2_interface:cbc_timed_solve_with_opts/6'
        """
        self.config = solver_config

        if 'mock' in solver_config and solver_config['mock']:  # For unit tests
            self.path = path
        else:
            self.path = os.path.expandvars(path)
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
        self.res_var = self.config.get('call_result_var', 'Res')

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

        if info and self.res_var in info:
            info = self._translate_solution(info[self.res_var])

        return answer, info

    def _translate_solution(self, solution):
        if not solution['type'] == 'compound' or not solution['value'][0] == 'solution':
            raise ValueError(f"Invalid solution format: {solution}")
        solution_list = solution['value'][1][0]
        solution_list = answerparser.translate_prolog_dot_list(solution_list)

        solution_dict = {}
        for binding in solution_list:
            binding_data = binding['value'][1]
            identifier = binding_data[0]['value']
            value = self._translate_solution_value(binding_data[1]['value'],
                                                   binding_data[2]['value'])
            solution_dict[identifier] = value
        return solution_dict

    def _translate_solution_value(self, value, pprint=None):
        if pprint ==  '{}':
            # Empty set special case
            return set([])

        if type(value) is tuple:
            typ = value[0]
            val = value[1]
            if typ == 'int':
                return val[0]['value']
            elif typ == 'floating':
                return val[0]['value']
            elif typ == 'avl_set':
                bset =  set(self._translate_avl_set(val[0]))
                # This could be a sequence.
                if bseq := self._translate_bseq(bset):
                    return bseq
                else:
                    return bset
            elif typ == 'string':
                return val[0]['value']
            elif typ == 'term':
                if val[0]['value'][0] == 'floating':
                    return val[0]['value'][1][0]['value']
            elif typ == ',':
                lhs = self._translate_solution_value(val[0]['value'])
                rhs = self._translate_solution_value(val[1]['value'])
                return (lhs, rhs)

        return value

    def _translate_avl_set(self, value) -> list:
        # AVL layout: node(Value, True, Balance, Left, Right)
        if value['value'] == 'empty':
            return []

        result = []
        val = value['value'][1][0]['value']
        truth = value['value'][1][1]
        left = value['value'][1][3]
        right = value['value'][1][4]

        trans_val = self._translate_solution_value(val)
        result.append(trans_val)
        result += self._translate_avl_set(left)
        result += self._translate_avl_set(right)

        return result

    def _translate_bseq(self, bset):
        if len(bset) == 0:
            return None

        probe = next(iter(bset))
        if not isinstance(probe, tuple):
            return None

        if not isinstance(probe[0], int):
            return None

        # Per B's type system, all elements are tuples with int-lhs
        d = dict(bset)
        bseq = []
        for i in range(1, len(bset)+1):
            if i not in d:
                return None
            bseq.append(d[i])

        return bseq
