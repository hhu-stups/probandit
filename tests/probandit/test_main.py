from unittest.mock import patch

from probandit.solver import Solver
from probandit.__main__ import eval_solvers


def test_eval_socket_timeout():
    with patch('probandit.solver.Solver.solve', side_effect=TimeoutError):
        with patch('probandit.solver.Solver.restart'):
            s = Solver(path='foo', id='foo', mock=True)

            expected = {'foo': ('no', 'Socket timeout', 600)}
            actual = eval_solvers([s], 'pred', 'env',
                                discard_socket_timeouts=False)

            assert actual == expected


def test_eval_discard_socket_timeout():
    with patch('probandit.solver.Solver.solve', side_effect=TimeoutError):
        with patch('probandit.solver.Solver.restart'):
            s = Solver(path='foo', id='foo', mock=True)

            expected = None
            actual = eval_solvers([s], 'pred', 'env',
                                discard_socket_timeouts=True)

            assert actual == expected
