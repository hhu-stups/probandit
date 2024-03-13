from probandit.solver import Solver


def test_integer_translation():
    value = ('int', [{'type': 'number', 'value': 2}])

    s = Solver(path='foo', mock=True)

    expected = 2
    actual = s._translate_solution_value(value)

    assert actual == expected


def test_avl_translation():
    value = ('avl_set',
             [{'type': 'compound',
               'value':
               ('node',
                [{'type': 'compound', 'value': ('int', [{'type': 'number', 'value': 2}])},
                 {'type': 'atom', 'value': 'true'},
                 {'type': 'number', 'value': 1},
                 {'type': 'atom', 'value': 'empty'},
                 {'type': 'compound', 'value':
                  ('node', [{'type': 'compound', 'value': ('int', [{'type': 'number', 'value': 3}])},
                            {'type': 'atom', 'value': 'true'},
                            {'type': 'number', 'value': 0},
                            {'type': 'atom', 'value': 'empty'},
                            {'type': 'atom', 'value': 'empty'}])}])}])

    s = Solver(path='foo', mock=True)

    expected = {2, 3}
    actual = s._translate_solution_value(value)

    assert actual == expected


def test_string_translation():
    value = ('string', [{'type': 'atom', 'value': 'hello world'}])

    s = Solver(path='foo', mock=True)

    expected = "hello world"
    actual = s._translate_solution_value(value)

    assert actual == expected


def test_floating_translation():
    value = ('floating', [{'type': 'number', 'value': 2.5}])

    s = Solver(path='foo', mock=True)

    expected = 2.5
    actual = s._translate_solution_value(value)

    assert actual == expected


def test_floating_term_translation():
    value = ('term', [{'type': 'compound',
                       'value': ('floating',
                                 [{'type': 'number', 'value': 2.5}])}])

    s = Solver(path='foo', mock=True)

    expected = 2.5
    actual = s._translate_solution_value(value)

    assert actual == expected


def test_tuple_translation():
    value = (',', [{'type': 'compound',
                    'value': ('int', [{'type': 'number', 'value': 0}])},
                   {'type': 'compound',
                    'value': ('int', [{'type': 'number', 'value': 1}])}])

    s = Solver(path='foo', mock=True)

    expected = (0, 1)
    actual = s._translate_solution_value(value)

    assert actual == expected


def test_bseq_translation():
    value = {(1, 'a'), (2, 'b'), (3, 'c')}

    s = Solver(path='foo', mock=True)

    expected = ['a', 'b', 'c']
    actual = s._translate_bseq(value)

    assert actual == expected


def test_bseq_translation_failing():
    value = {(1, 'a'), (2, 'b'), (4, 'c')}  # Not a proper sequence

    s = Solver(path='foo', mock=True)

    expected = None
    actual = s._translate_bseq(value)

    assert actual == expected


def test_contradiction_found():
    value = {'type': 'atom', 'value': 'contradiction_found'}

    s = Solver(path='foo', mock=True)

    expected = None
    actual = s._translate_solution(value)

    assert actual == expected
