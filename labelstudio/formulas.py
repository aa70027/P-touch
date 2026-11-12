"""Small expression language. No Python eval, attribute access, I/O or loops."""
import ast
import operator
import re

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Mod: operator.mod, ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Gt: operator.gt,
       ast.GtE: operator.ge, ast.Lt: operator.lt, ast.LtE: operator.le, ast.In: lambda a,b: a in b,
       ast.NotIn: lambda a,b: a not in b}


def evaluate(expression, row):
    if len(expression) > 2000:
        raise ValueError('FORMULA_TOO_LONG')
    tree = ast.parse(expression, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 150:
        raise ValueError('FORMULA_TOO_COMPLEX')

    def visit(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (str, int, float, bool, type(None))):
            return n.value
        if isinstance(n, ast.Name):
            return row.get(n.id, '')
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and not n.keywords:
            name = n.func.id.upper()
            # IF is lazy: unused branches may contain missing or invalid data.
            if name == 'IF' and len(n.args) == 3:
                return visit(n.args[1]) if visit(n.args[0]) else visit(n.args[2])
            args = [visit(a) for a in n.args]
            funcs = {'COL': lambda key: row.get(str(key), ''), 'EMPTY': lambda v: v is None or str(v).strip() == '',
                     'UPPER': lambda v: str(v).upper(), 'LOWER': lambda v: str(v).lower(),
                     'TRIM': lambda v: str(v).strip(), 'TEXT': str, 'NUMBER': float,
                     'CONCAT': lambda *v: ''.join(map(str, v)), 'LEN': lambda v: len(str(v)),
                     'PAD': lambda v, n: str(v).zfill(min(100, int(n))),
                     'REPLACE': lambda v, a, b: str(v).replace(str(a), str(b)),
                     'CONTAINS': lambda v, p: str(p) in str(v), 'ROUND': round,
                     'AND': lambda *v: all(v), 'OR': lambda *v: any(v), 'NOT': lambda v: not v}
            if name not in funcs:
                raise ValueError('UNKNOWN_FUNCTION:' + name)
            value = funcs[name](*args)
        elif isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                return all(visit(x) for x in n.values)
            return any(visit(x) for x in n.values)
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.Not, ast.USub, ast.UAdd)):
            value = visit(n.operand)
            return not value if isinstance(n.op, ast.Not) else -value if isinstance(n.op, ast.USub) else +value
        elif isinstance(n, ast.Compare):
            left = visit(n.left)
            for op, right_node in zip(n.ops, n.comparators):
                right = visit(right_node)
                if type(op) not in OPS or not OPS[type(op)](left, right):
                    return False
                left = right
            return True
        elif isinstance(n, ast.IfExp):
            return visit(n.body) if visit(n.test) else visit(n.orelse)
        elif isinstance(n, ast.BinOp) and type(n.op) in OPS:
            left, right = visit(n.left), visit(n.right)
            if isinstance(n.op, ast.Mult) and (isinstance(left, str) or isinstance(right, str)):
                if len(str(left)) * (right if isinstance(right, int) else len(str(right))) > 8000:
                    raise ValueError('FORMULA_OUTPUT_TOO_LONG')
            value = OPS[type(n.op)](left, right)
        else:
            raise ValueError('UNSUPPORTED_EXPRESSION')
        if isinstance(value, str) and len(value) > 8000:
            raise ValueError('FORMULA_OUTPUT_TOO_LONG')
        if isinstance(value, (int, float)) and abs(value) > 1e15:
            raise ValueError('FORMULA_NUMBER_TOO_LARGE')
        return value
    return visit(tree.body)


def apply_rules(row, rules, variables=None):
    result = dict(variables or {}) | dict(row)
    for rule in rules:
        target = str(rule.get('target', '')).strip()
        if not target:
            raise ValueError('RULE_TARGET_REQUIRED')
        when = str(rule.get('when', 'True')) or 'True'
        if evaluate(when, result):
            result[target] = evaluate(str(rule.get('value', "''")), result)
        elif 'otherwise' in rule and str(rule['otherwise']).strip():
            result[target] = evaluate(str(rule['otherwise']), result)
    return result


def interpolate(text, row):
    if text.startswith('='):
        return str(evaluate(text[1:], row))
    # Double braces are escaped literal braces.
    text = text.replace('{{', '\x00').replace('}}', '\x01')
    text = re.sub(r'\{([^{}]+)\}', lambda m: str(row.get(m.group(1), '')), text)
    return text.replace('\x00', '{').replace('\x01', '}')
