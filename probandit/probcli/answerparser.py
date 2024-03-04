# b"yes('.'(=('Major',1),'.'(=('Minor',13),'.'(=('Service',1),'.'(=('Qualifier',nightly),'.'(=('GitRevision','87f2186466c702f5f1c272df71573fb1afb6288e'),'.'(=('LastChangedDate','Thu Feb 29 19:14:56 2024 +0100'),'.'(=('PrologInfo','SICStus 4.8.0 (x86_64-linux-glibc2.17): Sun Dec  4 13:17:40 UTC 2022'),[]))))))))\n\x01"

def parse_term(answer):
    # term = {number} number
    #      | {variable} variable
    #      | {atom} name
    #      | {list} l_sq params r_sq
    #      | {compound} [functor]:name l_par params r_par;
    type = None
    if answer[0] in '0123456789.+-':
        term, answer = parse_number(answer)
        type = 'number'
    elif answer[0].isupper() or answer[0] == '_':
        term, answer = parse_var(answer)
        type = 'variable'
    elif answer[0].islower() or answer[0] == '\'' or answer[0] in '+-*/\\^<>=~:.?@#$&!;':
        term, answer = parse_atom(answer)
        type = 'atom'
        if answer and answer[0] == '(':
            type = 'compound'
            answer = consume('(', answer)
            args, answer = parse_terms(answer)
            term = (term, args)
            answer = consume(')', answer)
    elif answer[0] == '[':
        type = 'list'
        answer = consume('[', answer)
        if answer[0] == ']':
            term = []
        else:
            term, answer = parse_terms(answer)
        answer = consume(']', answer)
    else:
        raise ValueError(f"Expected term, got {answer}")

    return {'type': type, 'value': term}, answer


def parse_terms(answer):
    terms = []
    while answer:
        if answer[0].isspace():
            answer = trim_whitespace(answer)
        else:
            term, answer = parse_term(answer)
            terms.append(term)
            if answer:
                answer = trim_whitespace(answer)
            if answer and answer[0] == ',':
                answer = consume(',', answer)
            else:
                break
    return terms, answer


def translate_prolog_dot_list(dot_compound):
    """
    Translates a parsed prolog list in dot notation into a python list.
    """
    elems = []
    if dot_compound['type'] == 'list':
        return dot_compound['value']
    elif dot_compound['type'] == 'compound' and dot_compound['value'][0] == '.':
        elems.append(dot_compound['value'][1][0])
        elems.extend(translate_prolog_dot_list(dot_compound['value'][1][1]))
    else:
        raise ValueError(f"Expected prolog list, got {dot_compound}")
    return elems


def translate_bindings(bindings_list):
    """
    Translates a list of =/2 compounds into a dictionary.
    Assumes that `translate_prolog_dot_list` has been applied to the values
    if necessary.
    """
    bindings = {}
    for binding in bindings_list:
        if binding['type'] != 'compound' or binding['value'][0] != '=':
            raise ValueError(f"Expected binding over =/2, got {binding}")
        if len(binding['value'][1]) != 2:
            raise ValueError(f"Expected binding over =/2, got {binding}")
        key = binding['value'][1][0]
        value = binding['value'][1][1]
        bindings[key] = value
    return bindings


def parse_number(answer):
    # number = {float} float
    #        | {integer} integer;
    sign = 1
    num = None
    if answer[0] in '+-':
        if answer[0] == '-':
            sign = -1
        answer = answer[1:]
    if answer.startswith('0b'):
        num, answer = parse_int_format(answer[2:], 2)
    elif answer.startswith('0o'):
        num, answer = parse_int_format(answer[2:], 8)
    elif answer.startswith('0x'):
        num, answer = parse_int_format(answer[2:], 16)
    # Todo: quoted_atom_item ?
    elif answer[0] == '.':  # . digit+
        answer = consume('.', answer)
        exp = ''
        if answer[0].isdigit():
            numstr, answer = parse_int_format(answer, 10, cast_to_int=False)
        if answer and answer[0] in 'eE':
            exp, answer = parse_int(answer[1:], cast_to_int=False)
            exp = 'E' + exp
        numstr = f'.{numstr}{exp}'
        # parse float
        num = float(numstr)
    else:
        numstr, answer = parse_int_format(answer, 10, cast_to_int=False)
        is_float = False
        if answer and answer[0] == '.':
            answer = consume('.', answer)
            numstr2, answer = parse_int_format(answer, 10, cast_to_int=False)
            numstr += f'.{numstr2}'
            is_float = True
        if answer and answer[0] in 'eE':
            exp, answer = parse_int(answer[1:], cast_to_int=False)
            exp = 'E' + exp
            numstr += exp
            is_float = True
        if is_float:
            num = float(numstr)
        else:
            num = int(numstr)
    return sign * num, answer


def parse_int(answer, cast_to_int=True):
    sign = 1
    if answer[0] in '+-':
        if answer[0] == '-':
            sign = -1
        answer = answer[1:]
    num, answer = parse_int_format(answer, 10, cast_to_int=cast_to_int)

    if cast_to_int:
        return sign * num, answer
    else:
        s = '-' if sign == -1 else ''
        return s + num, answer


def parse_int_format(answer, base, cast_to_int=True):
    digits = '0123456789abcdef'[0:base]
    numstr = ''
    while answer:
        if answer[0].lower() in digits:
            numstr += answer[0]
            answer = answer[1:]
        else:
            break
    if cast_to_int:
        return int(numstr, base), answer
    else:
        return numstr, answer

def parse_var(answer):
    # variable = '_' alpha* | capital_letter alpha*;
    var = ''
    while answer and (answer[0].isalnum() or answer[0] == '_'):
        var += answer[0]
        answer = answer[1:]
    return var, answer

def parse_atom(answer):
    atom = ''
    if answer[0] == '\'':
        answer = consume('\'', answer)
        while answer and answer[0] != '\'':
            atom += answer[0]
            answer = answer[1:]
        answer = consume('\'', answer)
    elif answer[0] in '+-*/\\^<>=~:.?@#$&': # special characters
        while answer and (answer[0] in '+-*/\\^<>=~:.?@#$&'):
            atom += answer[0]
            answer = answer[1:]
    elif answer[0] in '!;': # Single chars
        atom = answer[0]
        answer = answer[1:]
    else:
        while answer and (answer[0].isalnum() or answer[0] == '_'):
            atom += answer[0]
            answer = answer[1:]
    return atom, answer


def consume(c, s):
    if s.startswith(c):
        return s[1:]
    else:
        raise ValueError(f"Expected {c}, got {s}")


def trim_whitespace(answer):
    while answer and answer[0].isspace():
        answer = answer[1:]
    return answer
