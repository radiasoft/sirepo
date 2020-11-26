# -*- coding: utf-8 -*-
u"""Code variables.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import lattice
from sirepo.template import template_common
import ast
import inspect
import math
import operator
import re


class CodeVar():

    _INFIX_TO_RPN = PKDict({
        ast.Add: '+',
        ast.Div: '/',
        ast.Invert: '!',
        ast.Mult: '*',
        ast.Not: '!',
        ast.Pow: 'pow',
        ast.Sub: '-',
        ast.USub: 'chs',
    })

    def __init__(self, variables, evaluator, case_insensitive=False):
        self.variables = self.__variables_by_name(variables, case_insensitive)
        self.postfix_variables = self.__variables_to_postfix(self.variables)
        self.evaluator = evaluator
        self.case_insensitive = case_insensitive

    def compute_cache(self, data, schema):
        if 'models' not in data:
            return None
        cache = lattice.LatticeUtil(data, schema).iterate_models(
            CodeVarIterator(self),
        ).result
        for name, value in self.variables.items():
            v, err = self.eval_var(value)
            if not err:
                if self.is_var_value(value):
                    if self.case_insensitive:
                        value = value.lower()
                    cache[value] = v
                else:
                    v = float(v)
                cache[name] = v
        data.models.rpnCache = cache
        return cache

    def eval_var(self, expr):
        if not self.is_var_value(expr):
            return expr, None
        if self.case_insensitive:
            expr = expr.lower()
        expr = self.infix_to_postfix(expr)
        return self.evaluator.eval_var(
            expr,
            self.get_expr_dependencies(expr),
            self.postfix_variables,
        )

    def eval_var_with_assert(self, expr):
        (v, err) = self.eval_var(expr)
        assert not err, f'expr={expr} err={err}'
        return float(v)

    def get_application_data(self, args, schema, ignore_array_values=False):
        from sirepo import simulation_db
        if args.method == 'rpn_value':
            if ignore_array_values and re.search(r'^\{.*\}$', args.value):
                # accept array of values enclosed in curly braces
                args.result = ''
                return True
            v, err = self.eval_var(args.value)
            if err:
                args.error = err
            else:
                args.result = v
            return True
        if args.method == 'recompute_rpn_cache_values':
            self.recompute_cache(args.cache)
            return True
        if args.method == 'validate_rpn_delete':
            model_data = simulation_db.read_json(
                simulation_db.sim_data_file(
                    args.simulationType,
                    args.simulationId,
                ))
            args.error = self.validate_var_delete(
                args.name,
                model_data,
                schema,
            )
            return True
        return False

    def get_expr_dependencies(self, expr, depends=None, visited=None):
        # expr must be in postfix format
        if depends is None:
            depends = []
            visited = {}
        if self.case_insensitive and self.is_var_value(expr):
            expr = expr.lower()
        for v in str(expr).split(' '):
            if v in self.postfix_variables:
                if v not in depends:
                    if v in visited:
                        # avoid circular dependencies
                        return depends
                    visited[v] = True
                    self.get_expr_dependencies(
                        self.postfix_variables[v],
                        depends,
                        visited,
                    )
                    depends.append(v)
        return depends

    def generate_variables(self, variable_formatter, postfix=False):
        res = ''
        visited = PKDict()
        variables = self.postfix_variables if postfix else self.variables
        for name in sorted(variables):
            for dependency in self.get_expr_dependencies(
                self.postfix_variables[name],
            ):
                res += variable_formatter(dependency, variables, visited)
            res += variable_formatter(name, variables, visited)
        return res

    def recompute_cache(self, cache):
        for k in cache:
            v, err = self.eval_var(k)
            if not err:
                cache[k] = v

    def validate_var_delete(self, name, data, schema):
        in_use = []
        for k, value in self.postfix_variables.items():
            if k == name:
                continue
            for v in str(value).split(' '):
                if v == name:
                    in_use.append(k)
        if in_use:
            return '"{}" is in use in variable(s): {}'.format(
                name,
                ', '.join(in_use),
            )
        in_use = lattice.LatticeUtil(data, schema).iterate_models(
            CodeVarDeleteIterator(self, name),
        ).result
        if in_use:
            return '"{}" is in use in element(s): {}'.format(
                name,
                ', '.join(in_use),
            )
        return None

    @classmethod
    def infix_to_postfix(cls, expr):
        try:
            if cls.is_var_value(expr):
                rpn = cls.__parse_expr_infix(expr)
                expr = rpn
        except Exception as e:
            pass
        return expr

    @classmethod
    def is_var_value(cls, value):
        if value:
            # is it a single value in numeric format?
            if template_common.NUMERIC_RE.search(str(value)):
                return False
            return True
        return False

    @classmethod
    def __parse_expr_infix(cls, expr):
        """Use Python parser (ast) and return depth first (RPN) tree"""

        # https://bitbucket.org/takluyver/greentreesnakes/src/587ad72894bc7595bc30e33affaa238ac32f0740/astpp.py?at=default&fileviewer=file-view-default

        def _do(n):
            # http://greentreesnakes.readthedocs.io/en/latest/nodes.html
            if isinstance(n, ast.Str):
                assert not re.search(r'^[^\'"]*$', n.s), \
                    '{}: invalid string'.format(n.s)
                return ['"{}"'.format(n.s)]
            elif isinstance(n, ast.Name):
                return [str(n.id)]
            elif isinstance(n, ast.Num):
                return [str(n.n)]
            elif isinstance(n, ast.Expression):
                return _do(n.body)
            elif isinstance(n, ast.Call):
                res = []
                for x in n.args:
                    res.extend(_do(x))
                return res + [n.func.id]
            elif isinstance(n, ast.BinOp):
                return _do(n.left) + _do(n.right) + _do(n.op)
            elif isinstance(n, ast.UAdd):
                return []
            elif isinstance(n, ast.UnaryOp):
                return _do(n.operand) + _do(n.op)
            elif isinstance(n, ast.IfExp):
                return _do(n.test) + ['?'] + _do(n.body) + [':'] \
                    + _do(n.orelse) + ['$']
            # convert an attribute-like value, ex. l.MQ, into a string "l.MQ"
            elif isinstance(n, ast.Attribute):
                return ['{}.{}'.format(_do(n.value)[0], n.attr)]
            else:
                x = CodeVar._INFIX_TO_RPN.get(type(n), None)
                if x:
                    return [x]
            raise ValueError('invalid node: {}'.format(ast.dump(n)))

        tree = ast.parse(expr, filename='eval', mode='eval')
        assert isinstance(tree, ast.Expression), \
            '{}: must be an expression'.format(tree)
        return ' '.join(_do(tree))

    def __variables_by_name(self, variables, case_insensitive):
        res = PKDict()
        for v in variables:
            n = v['name']
            value = v.get('value', 0)
            if case_insensitive:
                n = n.lower()
                if type(value) == str:
                    value = value.lower()
            res[n] = value
        return res

    def __variables_to_postfix(self, variables):
        res = PKDict()
        for name in variables:
            res[name] = self.infix_to_postfix(variables[name])
        return res


class CodeVarIterator(lattice.ModelIterator):
    def __init__(self, code_var):
        self.result = PKDict()
        self.code_var = code_var

    def field(self, model, field_schema, field):
        value = model[field]
        if field_schema[1] == 'RPNValue' and self.code_var.is_var_value(value):
            if self.code_var.case_insensitive:
                value = value.lower()
            if value not in self.result:
                v, err = self.code_var.eval_var(value)
                if not err:
                    self.result[value] = v


class CodeVarDeleteIterator(lattice.ModelIterator):
    def __init__(self, code_var, name):
        self.result = []
        self.code_var = code_var
        self.name = name

    def field(self, model, field_schema, field):
        if field_schema[1] == 'RPNValue' \
           and self.code_var.is_var_value(model[field]):
            for v in str(model[field]).split(' '):
                if v == self.name:
                    if lattice.LatticeUtil.is_command(model):
                        self.result.append('{}.{}'.format(model._type, field))
                    else:
                        self.result.append(
                            '{} {}.{}'.format(model.type, model.name, field),
                        )


class PurePythonEval():

    _OPS = PKDict({
        '*': operator.mul,
        '+': operator.add,
        '-': operator.sub,
        '/': operator.truediv,
        'abs': operator.abs,
        'acos': math.acos,
        'asin': math.asin,
        'atan': math.atan,
        'chs': operator.neg,
        'cos': math.cos,
        'pow': operator.pow,
        'sin': math.sin,
        'sqrt': math.sqrt,
        'tan': math.tan,
    })

    def __init__(self, constants=None):
        self.constants = constants or []

    def eval_var(self, expr, depends, variables):
        variables = variables.copy()
        for d in depends:
            v, err = PurePythonEval.__eval_python_stack(
                self,
                variables[d],
                variables,
            )
            if err:
                return None, err
            variables[d] = v
        return self.__eval_python_stack(expr, variables)

    @classmethod
    def postfix_to_infix(cls, expr):
        if not CodeVar.is_var_value(expr):
            return expr

        def __strip_parens(v):
            return re.sub(r'^\((.*)\)$', r'\1', v)

        values = str(expr).split(' ')
        stack = []
        for v in values:
            if v in cls._OPS:
                try:
                    op = cls._OPS[v]
                    args = list(reversed([stack.pop() for _ in range(_get_arg_count(op))]))
                    if v == 'chs':
                        stack.append('-{}'.format(args[0]))
                    elif re.search(r'\w', v):
                        stack.append('{}({})'.format(v, ','.join([__strip_parens(arg) for arg in args])))
                    else:
                        stack.append('({} {} {})'.format(args[0], v, args[1]))
                except IndexError:
                    # not parseable, return original expression
                    return expr
            else:
                stack.append(v)
        return __strip_parens(stack[-1])

    def __eval_python_stack(self, expr, variables):
        if not CodeVar.is_var_value(expr):
            return expr, None
        values = str(expr).split(' ')
        stack = []
        for v in values:
            if v in variables:
                stack.append(variables[v])
            elif v in self.constants:
                stack.append(self.constants[v])
            elif v in self._OPS:
                try:
                    op = self._OPS[v]
                    args = reversed(
                        [float(stack.pop()) for _ in range(_get_arg_count(op))],
                    )
                    stack.append(op(*args))
                except IndexError:
                    return None, 'too few items on stack'
                except ZeroDivisionError:
                    return None, 'division by zero'
            else:
                try:
                    stack.append(float(v))
                except ValueError:
                    return None, 'unknown token: {}'.format(v)
        return stack[-1], None


def _get_arg_count(fn):
    return len(inspect.signature(fn).parameters)
