from functools import wraps

import structlog


log = structlog.get_logger()

SAFE_BUILTINS = {
            'abs': abs,
            'all': all,
            'any': any,
            'ascii': ascii,
            'bin': bin,
            'bool': bool,
            'bytearray': bytearray,
            'bytes': bytes,
            'callable': callable,
            'chr': chr,
            'classmethod': classmethod,
            'complex': complex,
            'dict': dict,
            'dir': dir,
            'divmod': divmod,
            'enumerate': enumerate,
            'filter': filter,
            'float': float,
            'format': format,
            'frozenset': frozenset,
            'getattr': getattr,
            'hasattr': hasattr,
            'hash': hash,
            'hex': hex,
            'id': id,
            'int': int,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'iter': iter,
            'len': len,
            'list': list,
            'map': map,
            'max': max,
            'min': min,
            'next': next,
            'object': object,
            'oct': oct,
            'ord': ord,
            'pow': pow,
            'range': range,
            'repr': repr,
            'reversed': reversed,
            'round': round,
            'set': set,
            'slice': slice,
            'sorted': sorted,
            'str': str,
            'sum': sum,
            'super': super,
            'tuple': tuple,
            'type': type,
            'zip': zip
        }


class Check:
    def __init__(self, name, expr, error_msg=None):
        self.name = name
        self.expr = expr
        self._expr_obj = None
        self.error_msg = error_msg

    def compile(self):
        return compile(self.expr, '<string>', 'eval')

    @property
    def expr_obj(self):
        """Caches the compiled expression"""
        if self._expr_obj is None:
            self._expr_obj = compile(self.expr, '<string>', 'eval')
        return self._expr_obj

    def verify(self, globals_d=None, locals_d=None):
        """Evaluates the expression.
        Will pass locals and globals to `eval`"""

        # Filter builtins to prevent `__import__` shenanigans
        # and other attacks in the expression
        if isinstance(globals_d, dict):
            globals_d['__builtins__'] = SAFE_BUILTINS

        return eval(self.expr_obj, globals_d, locals_d)


class CheckList:
    def __init__(self, checks):
        self.checks = {c.name: c for c in checks}

    def __getattr__(self, item):
        return self.checks[item]


def check_all(*checks):
    """Transition decorator, raises an exception if any of the checks fails."""

    def _check_all(f):
        @wraps(f)
        def wrapper(instance, *args, **kwargs):
            for check in checks:
                cond = getattr(instance.checks, check)
                if not cond.verify({'doc': instance}):
                    log.error('Check failed', name=check, error=cond.error_msg)
                    raise Exception(cond.error_msg)
            return f(instance, *args, **kwargs)

        return wrapper

    return _check_all


def check_any(*checks):
    """Transition decorator, raises an exception if all of the checks fail."""

    def _check_any(f):
        @wraps(f)
        def wrapper(instance, *args, **kwargs):
            failures = []
            for check in checks:
                cond = getattr(instance.checks, check)
                if not cond.verify({'doc': instance}):
                    failures.append((check, cond.error_msg))
            if len(failures) == len(checks):
                log.error('All checks failed', transition=f.__name__, checks=checks)
                raise Exception(f'All checks failed for {f.__name__}')
            else:
                return f(instance, *args, **kwargs)

        return wrapper

    return _check_any
