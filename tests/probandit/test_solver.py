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

    expected = ('a', 'b', 'c')
    actual = s._translate_bseq(value)

    assert actual == expected


def test_bseq_translation_failing():
    value = {(1, 'a'), (2, 'b'), (4, 'c')}  # Not a proper sequence

    s = Solver(path='foo', mock=True)

    expected = None
    actual = s._translate_bseq(value)

    assert actual == expected


def test_call_options():
    call_opts = ['foo', 'bar']

    s = Solver(path='foo', mock=True, call_options=call_opts)

    expected = ['foo', 'bar']
    actual = s.call_opts

    assert actual == expected


def test_singular_call_option():
    call_opts = 'clean_up_pred'

    s = Solver(path='foo', mock=True, call_options=call_opts)

    expected = ['clean_up_pred']
    actual = s.call_opts

    assert actual == expected


def test_call_option_string():
    call_opts = ['foo', 'bar']

    s = Solver(path='foo', mock=True, call_options=call_opts)

    expected = "[foo, bar]"
    actual = s._call_option_string

    assert actual == expected


def test_empty_call_option_string():
    call_opts = []

    s = Solver(path='foo', mock=True, call_options=call_opts)

    expected = "[]"
    actual = s._call_option_string

    assert actual == expected


def test_cli_preferences():
    cli_preferences = ['foo', 'bar baz']

    s = Solver(path='foo', mock=True, cli_preferences=cli_preferences)

    expected = ['-p', 'foo', '-p', 'bar', 'baz']
    actual = s._cli_args

    assert actual == expected


def test_cli_preferences_as_dict():
    cli_preferences = {'foo': 'bar', 'baz': False}

    s = Solver(path='foo', mock=True, cli_preferences=cli_preferences)

    expected = ['-p', 'foo', 'bar', '-p', 'baz', 'FALSE']
    actual = s._cli_args

    assert actual == expected


def test_singular_cli_preference():
    cli_preferences = 'foo'

    s = Solver(path='foo', mock=True, cli_preferences=cli_preferences)

    expected = ['-p', 'foo']
    actual = s._cli_args

    assert actual == expected
