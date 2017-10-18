"""
Transition utils and mixin skeletons
"""

# TODO: Find a way to inject transitions dynamically at runtime


from functools import wraps


def keep_history(f):
    """
    Transition traceability decorator.
    Preserves the user/transition details in history.
    """
    @wraps(f)
    def wrapper(instance, *args, **kwargs):
        if args and kwargs.get('user') is None:
            user = args[0]
        elif kwargs.get('user') is not None:
            user = kwargs['user']
        else:
            user = kwargs['user'] = 'UNKNOWN'
        instance.history.append(f'{user}: {f.__name__}')
        return f(instance, *args, **kwargs)

    return wrapper


class Prepare:
    def prepare(self, user):
        pass


class Finish:
    def finish(self, user):
        pass


class Submit:
    def submit(self, user):
        pass


class Cancel:
    def cancel(self, user):
        pass


class Approve:
    def approve(self, user):
        pass


class Reject:
    def reject(self, user):
        pass
