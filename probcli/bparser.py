import socket
import subprocess
from typing import Union, NoReturn

from probcli.answerparser import parse_term


class BParser():

    def __init__(self, jar_path):
        """
        Parameters
        ----------
        jar_path : str
            The path to the BParser jar file.
        """
        self.jar = jar_path

        # Start the ProB CLI Parser server
        args = ['java', '-jar', self.jar, '-prepl']
        process = subprocess.Popen(args,
                                   stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE)

        # Get reported port
        l = process.stdout.readline().decode('utf-8').strip()
        dot_pos = l.find('.')
        self.port = int(l[:dot_pos])  # Port has format "\d+\.", e.g. "41835."

        # Connect to the server
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(('localhost', self.port))

    def parse_to_prolog(self, text) -> Union[str, NoReturn]:
        """
        Parses a given classical B predicate into a Prolog AST.
        Throws an exception if the parsing fails.
        """
        self._socket.sendall(b'predicate\n')
        self._socket.sendall(text.encode('utf-8') + b'\n')

        parsed = self._receive_answer()
        if parsed.startswith('parse_exception'):
            exception = parse_term(parsed)
            exception_text = exception[0]['value'][1][1]['value']
            raise ValueError(f'Parsing failed: {exception_text}')

        return parsed

    def _receive_answer(self):
        data = b''
        while True:
            data += self._socket.recv(1024)
            if b'\n' in data:  # Parser terminates with \n
                break

        return data.decode('utf-8').strip('\n')

    def __del__(self):
        self._socket.sendall(b'halt\n')
        self._socket.close()
