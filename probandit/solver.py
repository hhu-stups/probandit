import logging
import os

import probcli.answerparser as answerparser
from probcli import ProBCli


class Solver():

    def __init__(self, path, id=None, **solver_config):
        """
        Create a new Solver object. The configuration is a dictionary with
        the following keys (also see the solver configuration section in the
        README.md):

        - path (mandatory): the path to the solver binary
        - base_solver (optional): the base solver to use
            - one of 'PROB', 'KODKOD', 'Z3', 'Z3AXM', 'Z3CNS', 'CDCLT'
            - Default is 'PROB'
        - preferences (optional): a list of ProBCli preferences
        - prolog_call (optional): the Prolog call used to evaluate a predicate.
            - Use $pred as a placeholder for the predicate
            - Use $base as a placeholder for the base solver
            - Use $options as a placeholder for the call options
            - Default is 'prob2_interface:cbc_timed_solve_with_opts/6'
        - call_options (optional): a list of options passed to the prolog_call
        - call_result_var (optional): the name of the variable in the Prolog
            call that contains the result
            - Default is 'Res'
        - call_time_var (optional): the name of the variable in the Prolog call
            that contains the time it took to solve the predicate
            - Default is 'Msec'
        """
        self.config = solver_config
        self.id = id

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

        self.pred_call = self.config.get('prolog_call', None)
        self.call_opts = self.config.get('call_options', '[]')
        if self.pred_call is None:
            self.pred_call = f'cbc_timed_solve_with_opts($base,$options,$pred,_,Res,Msec)'
            self.pred_call = self.pred_call.replace('$base', self.base_solver)
        self.res_var = self.config.get('call_result_var', 'Res')
        self.time_var = self.config.get('call_time_var', 'Msec')

        self._cli_args = []
        if isinstance(self.preferences, dict):
            self.preferences = [self.preferences]
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

        self.solver_timeout = 2500
        for i, arg in enumerate(self._cli_args):
            if arg == '-p':
                key = self._cli_args[i+1]
                if key.lower() in ['time_out', 'timeout']:
                    self.solver_timeout = int(self._cli_args[i+2])
                    break

    def start(self, port=None):
        used_port = self.cli.start(port, self._cli_args)
        self.port = used_port

    def with_cli_at(self, port):
        self.cli = ProBCli(self.path)
        self.cli.connect(port)
        self.port = port

    def close(self):
        self.cli.close()
        self.port = None

    def restart(self, port=None):
        self.close()
        self.start(port)

    def solve(self, predicate, sequence_like_as_list=True):
        """
        Attempt to solve the given predicate and return the answer

        Parameters:
        - predicate: the predicate to solve as string in ASCII B syntax
        - sequence_like_as_list: if True, translate sets which correspond
          to sequences into lists. For instance, "f:{1,2}-->{1,2}" would
          have the solution 'f': [1, 1] instead of 'f': {(1,1), (2,1)}.

        Returns:
        - answer: the answer from the solver
        - info: additional information from the solver.
          - For 'yes' answers:
            - Info is a tuple (type, bindings)
            - type can be 'solution', 'contradiction_found', 'time_out',
              'no_solution_found', or 'error'
            - For 'solution' type, bindings is a dictionary with the
              respective variable bindings
            - For 'error' type, bindings is a string with the error message
        - time: The time it took to solve the predicate. This is usually in
          milliseconds, if the used `prolog_call` is not using different
          time unit. The value -1 indicates that the time measurement was not
          possible.
        """
        parsed_pred = self.cli.parser.parse_to_prolog(predicate)
        query = self.pred_call.replace('$pred', parsed_pred)
        query = query.replace('$options', self.call_opts)

        self.cli.send_prolog(query)
        answer, info = self.cli.receive_prolog()

        time = -1
        if info and self.time_var in info:
            time = self._translate_solution_value(info[self.time_var]['value'])

        if answer == 'yes' and info and self.res_var in info:
            res = info[self.res_var]

            yes_type = res['value']
            yes_info = None

            if yes_type == 'contradiction_found':
                ...
            elif yes_type == 'time_out':
                ...
            elif isinstance(yes_type, tuple) and yes_type[0] == 'no_solution_found':
                yes_info = yes_type[1]
                yes_type = yes_type[0]
            elif yes_type == 'error':
                yes_info = self._read_cli_error()
            else:
                yes_type = 'solution'
                yes_info = self._translate_solution(res,
                                                seq_as_list=sequence_like_as_list)

            info = (yes_type, yes_info)
        elif answer == 'no':
            # ProB should print errors to stderr.
            info = self._read_cli_error()

        return answer, info, time

    def _translate_solution(self, solution, seq_as_list=True):
        if not solution['type'] == 'compound' or not solution['value'][0] == 'solution':
            raise ValueError(f"Invalid solution format: {solution}")
        solution_list = solution['value'][1][0]
        solution_list = answerparser.translate_prolog_dot_list(solution_list)

        solution_dict = {}
        for binding in solution_list:
            binding_data = binding['value'][1]
            identifier = binding_data[0]['value']
            logging.debug("Translating binding: %s", binding_data)
            value = self._translate_solution_value(binding_data[1]['value'],
                                                   binding_data[2]['value'],
                                                   seq_as_list=seq_as_list)
            solution_dict[identifier] = value
        return solution_dict

    def _translate_solution_value(self, value, pprint=None, seq_as_list=True):
        if pprint == '{}':
            # Empty set special case
            return frozenset()
        elif value == []:
            return frozenset(frozenset())

        if value == 'contradiction_found':
            return None
        if type(value) is tuple:
            typ = value[0]
            val = value[1]
            if typ == 'int':
                return val[0]['value']
            elif typ == 'floating':
                return val[0]['value']
            elif typ == 'avl_set':
                bset = frozenset(self._translate_avl_set(val[0]))
                # This could be a sequence.
                if seq_as_list:
                    if bseq := self._translate_bseq(bset):
                        return bseq
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
            elif typ == 'global_set':
                return val[0]['value']
            else:
                raise ValueError(f"Unknown type: {typ}; value: {val}")
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

        return tuple(bseq)

    def _read_cli_error(self):
        try:
            info = self.cli.cli_process.stderr.readline().decode('utf-8').strip()
            info += self.cli.cli_process.stderr.readline().decode('utf-8').strip()
            info += self.cli.cli_process.stderr.readline().decode('utf-8').strip()
        except TimeoutError:
            info = "No error message available"
        return info
