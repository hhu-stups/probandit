from probcli.answerparser import parse_term, translate_prolog_dot_list, translate_bindings


def test_parse_atom_basic():
    answer = 'atom'
    result, rest = parse_term(answer)
    assert result == {'type': 'atom', 'value': 'atom'}
    assert rest == ''


def test_parse_atom_with_underscore():
    answer = 'atom_with_underscore'
    result, rest = parse_term(answer)
    assert result == {'type': 'atom', 'value': 'atom_with_underscore'}
    assert rest == ''


def test_parse_atom_with_numbers():
    answer = 'atom123'
    result, rest = parse_term(answer)
    assert result == {'type': 'atom', 'value': 'atom123'}
    assert rest == ''


def test_parse_atom_quoted():
    answer = "'Hello my name is atom and I am here to say'"
    result, rest = parse_term(answer)
    assert result == {
        'type': 'atom',
        'value': 'Hello my name is atom and I am here to say'}
    assert rest == ''


def test_parse_variable():
    answer = 'X'
    result, rest = parse_term(answer)
    assert result == {'type': 'variable', 'value': 'X'}
    assert rest == ''


def test_parse_variable_with_underscore():
    answer = '_X'
    result, rest = parse_term(answer)
    assert result == {'type': 'variable', 'value': '_X'}
    assert rest == ''


def test_parse_variable_only_underscore():
    answer = '_'
    result, rest = parse_term(answer)
    assert result == {'type': 'variable', 'value': '_'}
    assert rest == ''


def test_parse_number_integer():
    answer = '123'
    result, rest = parse_term(answer)
    assert result == {'type': 'number', 'value': 123}
    assert rest == ''


def test_parse_number_binary():
    answer = '0b101'
    result, rest = parse_term(answer)
    assert result == {'type': 'number', 'value': 5}
    assert rest == ''


def test_parse_number_float():
    answer = '3.14'
    result, rest = parse_term(answer)
    assert result == {'type': 'number', 'value': 3.14}
    assert rest == ''


def test_parse_number_float_exponent():
    answer = '3.14e3'
    result, rest = parse_term(answer)
    assert result == {'type': 'number', 'value': 3140.}
    assert rest == ''


def test_parse_number_float_negative_exponent():
    answer = '3.14e-3'
    result, rest = parse_term(answer)
    assert result == {'type': 'number', 'value': 0.00314}
    assert rest == ''


def test_parse_number_float_sub_one():
    answer = '.14'
    result, rest = parse_term(answer)
    assert result == {'type': 'number', 'value': .14}
    assert rest == ''


def test_parse_number_float_sub_one_exponent():
    answer = '.14e2'
    result, rest = parse_term(answer)
    assert result == {'type': 'number', 'value': 14.0}
    assert rest == ''


def test_parse_empty_list():
    answer = '[]'
    result, rest = parse_term(answer)
    assert result == {'type': 'list', 'value': []}
    assert rest == ''


def test_parse_list():
    answer = '[a, 1]'
    result, rest = parse_term(answer)
    assert result == {'type': 'list', 'value': [
        {'type': 'atom', 'value': 'a'},
        {'type': 'number', 'value': 1}
    ]}
    assert rest == ''


def test_equality_compound():
    answer = "=(a, b)"
    result, rest = parse_term(answer)
    assert result == {'type': 'compound', 'value': ('=', [
        {'type': 'atom', 'value': 'a'},
        {'type': 'atom', 'value': 'b'}
    ])}
    assert rest == ''


def test_list_translation():
    answer = "'.'(a, '.'(b, []))"
    result, rest = parse_term(answer)
    lst = translate_prolog_dot_list(result)
    assert lst == [{'type': 'atom', 'value': 'a'},
                   {'type': 'atom', 'value': 'b'}]
    assert rest == ''


def test_translate_bindings():
    bindings = [
        {'type': 'compound',
         'value': ('=',
                   [{'type': 'atom', 'value': 'a'},
                    {'type': 'atom', 'value': 'b'}])},
        {'type': 'compound',
         'value': ('=',
                   [{'type': 'atom', 'value': 'x'},
                    {'type': 'atom', 'value': 'x'}])},
    ]
    result = translate_bindings(bindings)
    assert result == {'a': {'type': 'atom', 'value': 'b'},
                      'x': {'type': 'atom', 'value': 'x'}}


def test_empty_set_parse():
    answer = "binding(f,[],{})"
    result, rest = parse_term(answer)

    expected = {'type': 'compound',
                'value': ('binding',
                          [{'type': 'atom', 'value': 'f'},
                           {'type': 'list', 'value': []},
                           {'type': 'atom', 'value': '{}'}])}
    assert result == expected
    assert rest == ''
