"""Parse a grammar written in ECMArkup."""

from lexer import LexicalGrammar
import parse_pgen
import gen

tokenize_emug = LexicalGrammar(
    # the operators and keywords:
    "[ ] { } , ~ + ? <! == != but empty here lookahead no not of one or through",
    NL="\n",
    EQ=r':+',                           # any number of colons together
    T=r'`[^` \n]+`|```',                # terminals of the ES grammar, quoted with backticks
    CHR=r'<[A-Z]+>|U\+[0-9A-f]{4}',     # also terminals, denoting control characters
    NTCALL=r'(?:uri|[A-Z])\w*(?=\[)',   # nonterminals that will be followed by boolean parameters
    NT=r'(?:uri|[A-Z])\w*',             # nonterminals (also, boolean parameters)
    NTALT=r'\|[A-Z]\w+\|',              # nonterminals wrapped in vertical bars for no apparent reason
    PRODID=r'#[A-Za-z]\w*',             # the spec also gives a few productions names
    PROSE=r'>.*',                       # prose to the end of the line
    WPROSE=r'\[>[^]]*\]'                # prose wrapped in square brackets
    )


parse_emug_generic = gen.compile(parse_pgen.load_grammar("emug.pgen"))


SIGIL_FALSE = '~'
SIGIL_TRUE = '+'


class EmugBuilder:
    def grammar_P0(self, x): return x
    def grammar_P1(self, x, y): return x + y

    def nt_def_or_blank_line_P0(self, nl): return []
    def nt_def_or_blank_line_P1(self, nt_def): return [nt_def]

    def make_nt_def(self, lhs, eq, rhs_list):
        if isinstance(lhs, tuple):
            name, args = lhs
            return (name, eq, gen.Parameterized(args, rhs_list))
        else:
            return (lhs, eq, rhs_list)

    def nt_def_P0(self, nt_lhs, eq, nl, rhs_lines, nl2):
        # nt_lhs EQ NL rhs_lines NL
        assert nl == "\n"
        assert nl2 == "\n"
        return self.make_nt_def(nt_lhs, eq, rhs_lines)

    def nt_def_P1(self, nt_lhs, eq, one, of, nl, terminals, nl2):
        # nt_lhs EQ "one" "of" NL t_list_lines
        assert one == "one"
        assert of == "of"
        assert nl == "\n"
        assert nl2 == "\n"
        return self.make_nt_def(nt_lhs, eq, [[t] for t in terminals])

    def nt_lhs_P0(self, nt): return nt
    def nt_lhs_P1(self, name, ob, params, cb):
        # NTCALL [ params ]
        assert ob == '['
        assert cb == ']'
        return (name, params)

    def params_P0(self, param): return [param]
    def params_P1(self, params, comma, param): return params + [param]

    def param_P0(self, nt): return nt

    def t_list_lines_P0(self, line): return line
    def t_list_lines_P1(self, lines, line): return lines + line

    def t_list_line_P0(self, terminals, nl): return terminals

    def terminal_seq_P0(self, t): return [t]
    def terminal_seq_P1(self, ts, t): return ts + [t]

    def terminal_P0(self, t):
        assert t[0] == "`"
        assert t[-1] == "`"
        return t[1:-1]

    def terminal_P1(self, chr):
        raise ValueError("FAILED: %r" % chr)

    def rhs_lines_P0(self, line): return [line]
    def rhs_lines_P1(self, lines, line): return lines + [line]

    def rhs_line_P0(self, ifdef, rhs, prodid, nl):
        assert nl == "\n"
        result = rhs
        if ifdef is not None:
            name, value = ifdef
            result = gen.ConditionalRhs(name, value, result)
        return result

    def rhs_line_P1(self, prose, nl):
        assert nl == "\n"
        return prose

    def rhs_P0(self, symbols): return symbols

    def rhs_P1(self, ob, empty, cb):
        assert (ob, empty, cb) == ("[", "empty", "]")
        return []

    def ifdef_P0(self, ob, value, nt, cb):
        assert (ob, cb) == ("[", "]")
        return nt, value

    def symbols_P0(self, symbol): return [symbol]
    def symbols_P1(self, symbols, symbol): return symbols + [symbol]

    def symbol_P0(self, t):
        # terminal
        return t

    def symbol_P1(self, nt):
        # nonterminal
        return nt

    def symbol_P2(self, nt, q):
        # nonterminal `?`
        assert q == "?"
        return gen.Optional(nt)

    def symbol_P3(self, nt, but, not_, exclusion):
        # nonterminal "but not" exclusion
        assert but == "but"
        assert not_ == "not"
        return ('-', nt, exclusion)

    def symbol_P4(self, nt, but, not_, one, of, exclusion_list):
        # nonterminal "but not one of" exclusion_list
        assert (but, not_, one, of) == ("but", "not", "one", "of")
        return ('-', nt, exclusion_list)

    def symbol_P5(self, ob, lookahead, look_assert, cb):
        # [lookahead ...]
        assert (ob, lookahead, cb) == ('[', 'lookahead', ']')
        return look_assert

    def symbol_P6(self, n):
        return self.no_line_terminator_here(n)

    def no_line_terminator_here(self, ob, no, line_terminator, here, cb):
        assert (ob, no, line_terminator, here, cb) == ('[', 'no', 'LineTerminator', 'here', ']')
        return ("no-LineTerminator-here",)

    def nonterminal_P0(self, nt):
        return nt

    def nonterminal_P1(self, name, ob, args, cb):
        assert (ob, cb) == ('[', ']')
        return gen.Apply(name, tuple(args.items()))

    def args_P0(self, arg):
        return dict([arg])

    def args_P1(self, args, comma, arg):
        key, value = arg
        if key in args:
            raise ValueError("parameter passed multiple times")
        args[key] = value
        return args

    def arg_P0(self, sigil, argname):
        if sigil == '?':
            return (argname, gen.Var(argname))
        else:
            return (argname, sigil)

    def sigil_P0(self, value):
        return value

    def sigil_P1(self, q):
        assert q == '?'
        return '?'

    def definite_sigil_P0(self, sigil):
        assert sigil == SIGIL_FALSE
        return False

    def definite_sigil_P1(self, sigil):
        assert sigil == SIGIL_TRUE
        return True

    def exclusion_list_P0(self, exclusion): return [exclusion]
    def exclusion_list_P0(self, exclusions, exclusion): return exclusions + [exclusion]

    def exclusion_P0(self, t): return ("t", t)
    def exclusion_P1(self, nt): return ("nt", nt)
    def exclusion_P2(self, c1, through, c2):
        assert through == "through"
        return ("range", c1, c2)

    def lookahead_assertion_P0(self, eq, t):
        assert eq == "=="
        return gen.LookaheadRule(frozenset([t]), True)

    def lookahead_assertion_P1(self, ne, t):
        assert ne == "!="
        return gen.LookaheadRule(frozenset([t]), False)

    def lookahead_assertion_P2(self, notin, nt):
        assert notin == '<!'
        return ('?!', nt)

    def lookahead_assertion_P3(self, notin, ob, lookahead_exclusions, cb):
        assert (notin, ob, cb) == ("<!", '{', '}')
        if all(len(excl) == 1 for excl in lookahead_exclusions):
            return gen.LookaheadRule(frozenset(excl[0] for excl in lookahead_exclusions), False)
        raise ValueError("unsupported: lookahead > 1 token, " + repr(lookahead_exclusions))

    def lookahead_exclusions_P0(self, e): return [e]
    def lookahead_exclusions_P1(self, es, comma, e): return es + [e]

    def lookahead_exclusion_P0(self, e): return [e]
    def lookahead_exclusion_P1(self, es, e): return es + [e]

    def lookahead_exclusion_element_P0(self, t):
        return t

    def lookahead_exclusion_element_P1(self, no_lt_here):
        return no_lt_here


def finish_grammar(nt_defs, goals):
    terminal_set = set()

    def hack_rhs(rhs):
        for i, e in enumerate(rhs):
            if isinstance(e, str) and e[:1] == "`":
                if len(e) < 3 or e[-1:] != "`":
                    raise ValueError("I don't know what this is: " + repr(e) + "(in " + repr(rhs) + ")")
                rhs[i] = token = e[1:-1]
                terminal_set.add(token)

    grammar = {}
    variable_terminals = set()
    for nt_name, eq, rhs_list_or_lambda in nt_defs:
        if eq == "::":
            variable_terminals.add(nt_name)

        if isinstance(rhs_list_or_lambda, gen.Parameterized):
            grammar[nt_name] = rhs_list_or_lambda
        else:
            rhs_list = rhs_list_or_lambda
            for rhs in rhs_list:
                if not isinstance(rhs, list):
                    raise ValueError("invalid grammar: ifdef in non-function-call context")
                hack_rhs(rhs)
            if eq == ':':
                if nt_name in grammar:
                    raise ValueError("unsupported: multiple definitions for nt " + nt_name)
                grammar[nt_name] = rhs_list

    for t in terminal_set:
        if t in grammar:
            raise ValueError("grammar contains both a terminal `{}` and nonterminal {}".format(t, t))

    return gen.Grammar(grammar, goals, variable_terminals)


def parse_emug(text, filename=None, goals=None):
    tokens = tokenize_emug(text, filename=filename)
    return finish_grammar(parse_emug_generic(tokens, EmugBuilder()), goals=goals)