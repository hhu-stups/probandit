import os
import socket
import subprocess

import probcli.answerparser as answerparser
from probcli.bparser import BParser


class ProBCli():
    """
    ProBCli is a class to interact with the probcli binary.
    It works over a socket connection and can send Prolog queries to the
    probcli and receive the results. Results are parsed and returned as
    Python objects.

    The usage is as follows:

        cli = ProBCli('/path/to/probcli')
        used_port = cli.start()  # Connects to ProB via a new socket server.
        cli.send_prolog('some_prolog_query.')
        answer = cli.receive_prolog()  # Returns a Python object

        cli.close()  # Closes the connection to ProB
    """

    def __init__(self, path):
        self.path = path
        self.is_connected = False

        self.revision = None

        self.interrupt_id = None
        self.interrupt_cmd_path = None
        interrupt_path = os.path.dirname(self.path)
        interrupt_bin_name = ('send_user_interrupt.exe'
                              if os.name == 'nt' else 'send_user_interrupt')
        self.interrupt_cmd_path = os.path.join(interrupt_path,
                                               interrupt_bin_name)

        self._socket = None
        self.parser = None

    def start(self, port=None, args=[]):
        if self.is_connected:
            raise ValueError('Already connected')

        used_port = self._start_probcli_server(port, args)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(('localhost', used_port))

        self.is_connected = True

        parser_path = os.path.join(os.path.dirname(self.path),
                                   'lib', 'probcliparser.jar')
        self.parser = BParser(parser_path)

        return used_port

    def close(self):
        if not self.is_connected:
            raise ValueError('Not connected')

        if self.interrupt_cmd_path and os.path.exists(self.interrupt_cmd_path):
            self.send_interrupt()
        self._halt()

        self._socket.close()
        self.is_connected = False

        self.revision = None
        self.interrupt_id = None

    def _halt(self):
        self._socket.sendall(b'halt.\0')

    def send_interrupt(self):
        if not self.interrupt_cmd_path:
            raise ValueError('No interrupt command available')
        elif not os.path.exists(self.interrupt_cmd_path):
            raise ValueError('Interrupt command not found')
        subprocess.run([self.interrupt_cmd_path, str(self.interrupt_id)])

    def send_prolog(self, prolog):
        if prolog[-1] != '.':
            prolog += '.'
        self._socket.sendall(prolog.encode('utf-8') + b'\0')

    def receive_prolog(self):
        data = b''
        while True:
            data += self._socket.recv(1024)
            if b'\x01' in data:  # Prolog terminates with \x01
                break
        data = data.decode('utf-8').strip('\x01')
        return answerparser.parse_answer(data)

    def query_probcli_version_info(self):
        """
        Returns a dictionary with version information about the
        connected probcli.

        The information dictionary has the following keys:
        - Major
        - Minor
        - Service
        - Qualifier
        - GitRevision
        - LastChangedDate
        - PrologInfo
        """
        if not self.is_connected:
            raise ValueError('Not connected')

        cmd = ('get_version(Major,Minor,Service,Qualifier,GitRevision,'
               'LastChangedDate,PrologInfo).')

        self.send_prolog(cmd)
        raw_answer = self.receive_prolog()

        if raw_answer['type'] != 'compound':
            raise ValueError('Unable to load version info')

        raw_first_arg = raw_answer['value'][1][0]
        bind_list = answerparser.translate_prolog_dot_list(raw_first_arg)
        bindings = answerparser.translate_bindings(bind_list)

        # Ensure we only take the values as well.
        for b in bindings:
            bindings[b] = bindings[b]['value']

        return bindings

    def _start_probcli_server(self, port, args):
        call_args = [self.path]

        if port:
            call_args += ['-s', str(port)]
        else:
            call_args += ['-sf']

        call_args += args

        # Start the probcli binary as subprocess
        p = subprocess.Popen(call_args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        # When the cli is starting, it prints 6 lines to stdout
        used_port = self._check_probcli_startup_output(p)

        return used_port

    def _check_probcli_startup_output(self, p):
        def next_line():
            return p.stdout.readline().decode('utf-8').strip()

        l = next_line()
        if l != "Starting Socket Server":
            raise ValueError('Unexpected output from probcli, line 1: ' + l)

        l = next_line()
        if l.startswith('Application Path:'):
            used_path = l[18:]
        else:
            raise ValueError('Unexpected output from probcli, line 2: ' + l)

        l = next_line()
        if l.startswith('Port:'):
            used_port = int(l[6:])
        else:
            raise ValueError('Unexpected output from probcli, line 3: ' + l)

        l = next_line()
        if l.startswith('probcli revision:'):
            self.revision = l[18:]
        else:
            raise ValueError('Unexpected output from probcli, line 4: ' + l)

        l = next_line()
        if l.startswith('user interrupt reference id'):
            self.interrupt_id = int(l[29:])
        else:
            raise ValueError('Unexpected output from probcli, line 5: ' + l)

        l = next_line()
        if l != '-- starting command loop --':
            raise ValueError('Unexpected output from probcli, line 6: ' + l)

        return used_port
