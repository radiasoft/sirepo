# -*- coding: utf-8 -*-
"""Code variables.

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


class CodeVar:
    _INFIX_TO_RPN = PKDict(
        {
            ast.Add: "+",
            ast.Div: "/",
            ast.Invert: "!",
            ast.Mult: "*",
            ast.Not: "!",
            ast.Pow: "pow",
            ast.Sub: "-",
            ast.USub: "chs",
        }
    )

    def __init__(self, variables, evaluator, case_insensitive=False):
        self.case_insensitive = case_insensitive
        self.variables = self.__variables_by_name(variables)
        self.postfix_variables = self.__variables_to_postfix(self.variables)
        self.evaluator = evaluator

    def canonicalize(self, expr):
        if self.case_insensitive:
            return expr.lower()
        return expr

    def compute_cache(self, data, schema):
        if "models" not in data:
            return None
        it = CodeVarIterator(self, data, schema)
        cache = lattice.LatticeUtil(data, schema).iterate_models(it).result
        for name, value in self.variables.items():
            it.add_to_cache(name, value)
        data.models.rpnCache = cache
        return cache

    def eval_var(self, expr):
        if not self.is_var_value(expr):
            return expr, None
        expr = self.infix_to_postfix(self.canonicalize(expr))
        return self.evaluator.eval_var(
            expr,
            self.get_expr_dependencies(expr),
            self.postfix_variables,
        )

    def eval_var_with_assert(self, expr):
        (v, err) = self.eval_var(expr)
        assert not err, f"expr={expr} err={err}"
        try:
            return float(v)
        except ValueError:
            return v

    def get_expr_dependencies(self, expr, depends=None, visited=None):
        # expr must be in postfix format
        if depends is None:
            depends = []
            visited = {}
        if self.is_var_value(expr):
            expr = self.canonicalize(expr)
        for v in str(expr).split(" "):
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
        res = ""
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

    def stateful_compute_rpn_value(self, data, schema, **kwargs):
        v, err = self.eval_var(data.value)
        if err:
            data.error = err
        else:
            data.result = v
        return data

    def stateful_compute_recompute_rpn_cache_values(self, data, schema, **kwargs):
        self.recompute_cache(data.cache)
        return data

    def stateful_compute_validate_rpn_delete(self, data, schema, **kwargs):
        from sirepo import simulation_db

        model_data = simulation_db.read_json(
            simulation_db.sim_data_file(
                data.simulationType,
                data.simulationId,
            )
        )
        data.error = self.validate_var_delete(
            data.name,
            model_data,
            schema,
        )
        return data

    def validate_var_delete(self, name, data, schema):
        search = self.canonicalize(name)
        in_use = []
        for k, value in self.postfix_variables.items():
            if k == search:
                continue
            for v in str(value).split(" "):
                if v == search:
                    in_use.append(k)
                    break
        if in_use:
            return '"{}" is in use in variable(s): {}'.format(
                name,
                ", ".join(in_use),
            )
        in_use = (
            lattice.LatticeUtil(data, schema)
            .iterate_models(
                CodeVarDeleteIterator(self, search),
            )
            .result
        )
        if in_use:
            return '"{}" is in use in element(s): {}'.format(
                name,
                ", ".join(in_use),
            )
        return None

    @classmethod
    def infix_to_postfix(cls, expr):
        try:
            if cls.is_var_value(expr):
                expr = re.sub(r"\^", "**", expr)
                rpn = cls.__parse_expr_infix(expr)
                expr = rpn
            else:
                expr = float(expr)
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
                assert not re.search(r'^[^\'"]*$', n.s), "{}: invalid string".format(
                    n.s
                )
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
                return _do(n.test) + ["?"] + _do(n.body) + [":"] + _do(n.orelse) + ["$"]
            # convert an attribute-like value, ex. l.MQ, into a string "l.MQ"
            elif isinstance(n, ast.Attribute):
                return ["{}.{}".format(_do(n.value)[0], n.attr)]
            else:
                x = CodeVar._INFIX_TO_RPN.get(type(n), None)
                if x:
                    return [x]
            raise ValueError("invalid node: {}".format(ast.dump(n)))

        tree = ast.parse(expr, filename="eval", mode="eval")
        assert isinstance(tree, ast.Expression), "{}: must be an expression".format(
            tree
        )
        return " ".join(_do(tree))

    def __variables_by_name(self, variables):
        res = PKDict()
        for v in variables:
            # work-around for #4935 skip invalid variables
            if v is None or v["name"] is None:
                continue
            n = self.canonicalize(v["name"])
            value = v.get("value", 0)
            if self.case_insensitive and type(value) == str:
                value = value.lower()
            res[n] = value
        return res

    def __variables_to_postfix(self, variables):
        res = PKDict()
        for name in variables:
            res[name] = self.infix_to_postfix(variables[name])
        return res


class CodeVarIterator(lattice.ModelIterator):
    def __init__(self, code_var, data, schema):
        self.result = PKDict()
        self.code_var = code_var
        self.__add_beamline_fields(data, schema)

    def add_to_cache(self, name, value):
        v = self.__add_value(value)
        if v is not None:
            self.result[name] = v

    def field(self, model, field_schema, field):
        value = model[field]
        if field_schema[1] == "RPNValue":
            self.__add_value(value)

    def __add_beamline_fields(self, data, schema):
        if not schema.get("model") or not schema.model.get("beamline"):
            return
        bs = schema.model.beamline
        for bl in data.models.beamlines:
            if "positions" not in bl:
                continue
            for f in bs:
                if f in bl and bl[f]:
                    self.field(bl, bs[f], f)
            for p in bl.positions:
                for f in p:
                    if p[f] and self.code_var.is_var_value(p[f]):
                        self.add_to_cache(p[f], p[f])

    def __add_value(self, value):
        if self.code_var.is_var_value(value):
            value = self.code_var.canonicalize(value)
            if value not in self.result:
                v, err = self.code_var.eval_var(value)
                if err:
                    return None
                self.result[value] = v
            return self.result[value]
        return float(value) if value else 0


class CodeVarDeleteIterator(lattice.ModelIterator):
    def __init__(self, code_var, name):
        self.result = []
        self.code_var = code_var
        self.name = name

    def field(self, model, field_schema, field):
        if field_schema[1] == "RPNValue" and self.code_var.is_var_value(model[field]):
            expr = self.code_var.canonicalize(
                self.code_var.infix_to_postfix(str(model[field]))
            )
            for v in str(expr).split(" "):
                if v == self.name:
                    if lattice.LatticeUtil.is_command(model):
                        self.result.append("{}.{}".format(model._type, field))
                    else:
                        self.result.append(
                            "{} {}.{}".format(model.type, model.name, field),
                        )


class PurePythonEval:
    _OPS = PKDict(
        {
            "*": operator.mul,
            "+": operator.add,
            "-": operator.sub,
            "/": operator.truediv,
            "abs": operator.abs,
            "acos": math.acos,
            "asin": math.asin,
            "atan": math.atan,
            "chs": operator.neg,
            "cos": math.cos,
            "pow": operator.pow,
            "sin": math.sin,
            "sqrt": math.sqrt,
            "tan": math.tan,
        }
    )

    def __init__(self, constants=None):
        self.constants = constants or []

    def eval_var(self, expr, depends, variables):
        variables = variables.copy()
        for d in depends:
            # recurse eval_var, but with empty dependencies
            v, err = PurePythonEval.eval_var(
                self,
                self.__eval_indexed_variable(variables[d], variables),
                {},
                variables,
            )
            if err:
                return None, err
            variables[d] = v
        return self.__eval_python_stack(
            self.__eval_indexed_variable(expr, variables), variables
        )

    @classmethod
    def postfix_to_infix(cls, expr):
        if not CodeVar.is_var_value(expr):
            return expr

        def __strip_parens(v):
            return re.sub(r"^\((.*)\)$", r"\1", v)

        values = str(expr).split(" ")
        stack = []
        for v in values:
            if v in cls._OPS:
                try:
                    op = cls._OPS[v]
                    args = list(
                        reversed([stack.pop() for _ in range(_get_arg_count(op))])
                    )
                    if v == "chs":
                        stack.append("-{}".format(args[0]))
                    elif re.search(r"\w", v):
                        stack.append(
                            "{}({})".format(
                                v, ",".join([__strip_parens(arg) for arg in args])
                            )
                        )
                    else:
                        stack.append("({} {} {})".format(args[0], v, args[1]))
                except IndexError:
                    # not parseable, return original expression
                    return expr
            else:
                stack.append(v)
        return __strip_parens(stack[-1])

    def __eval_indexed_variable(self, expr, variables):
        if isinstance(expr, list):
            return [self.__eval_indexed_variable(e, variables) for e in expr]
        r = rf"(.*)({'|'.join(list(variables.keys()))})\s*\[\s*(\d+)\s*\]"
        if not re.match(r, str(expr)):
            return CodeVar.infix_to_postfix(expr)
        return self.__eval_indexed_variable(
            re.sub(
                r,
                lambda m: m.group(1) + str(variables[m.group(2)][int(m.group(3))]),
                expr,
            ),
            variables,
        )

    def __eval_python_stack(self, expr, variables):
        if not CodeVar.is_var_value(expr):
            return expr, None
        if isinstance(expr, list):
            evs = []
            # loop instead of map so we can fail out on the first error
            for e in expr:
                ev = self.__eval_python_stack(CodeVar.infix_to_postfix(e), variables)
                if ev[1] is not None:
                    return None, ev[1]
                evs.append(ev[0])
            return evs, None

        values = str(expr).split(" ")
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
                    return None, "too few items on stack"
                except ZeroDivisionError:
                    return None, "division by zero"
            else:
                try:
                    stack.append(float(v))
                except ValueError:
                    return None, "unknown token: {}".format(v)
        return stack[-1], None


def _get_arg_count(fn):
    return len(inspect.signature(fn).parameters)
