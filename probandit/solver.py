import os

class Solver():

    def __init__(self, solver_config):
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

    def get_socket_call(self, port=None):
        if port is None:
            port_switch = '-sf'  # Starts the repl on some free port
        else:
            port_switch = f'-s {port}'

        socket_call = f"{self.path} {port_switch}"

        prefs = ' '.join('-p ' + pref for pref in self.preferences)
        if len(prefs) > 0:
            socket_call += f' {prefs}'

        return socket_call
