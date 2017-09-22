"""
A short walkthrough of XWorkflows's features.

Adding custom functionality is demonstrated through user-defined transition checks
and check all/any decorators.

Logging is disabled during doctests
>>> log.debug = nolog
>>> log.error = nolog

The states and transitions defined in `ReportWorkflow` are enabled for the `Report` class.
`Report` instances have title, content and keywords attributes which will be validated by
a set of transition checks.

We specify checks as a dict of where values are (expression, error message) tuples.
The report instance will be exposed as `doc` to check locals.
>>> checks_list = {
...    'has_content': (
...        'doc.content is not None and len(doc.content) > 0',
...        'Content is empty'
...    ),
...    'has_keywords': (
...        'doc.keywords',
...        'No keywords defined'
...    ),
...    'title_size': (
...        'len(doc.title) >= 8',
...        'Title too short (at least 8 chars)'
...    )
... }
...

Checks are provided during report creation (TODO: allow dynamic checks)
>>> rep = Report(title='Report1', keywords=['bar'], checks=checks_list)

New reports start in the 'draft' state.
>>> rep.state.name
'draft'

Transitions are available as methods on the report:
>>> rep.prepare('Larry')

The state has changed after the transition:
>>> rep.state.title
'Ready'

User 'Curly' tries to move the report into the 'Complete' state,
but the `finish` transition has to satisfy a couple of checks:
>>> rep.finish('Curly')
Traceback (most recent call last):
...
Exception: Content is empty
>>> rep.content = 'foo'
>>> rep.finish('Curly')
Traceback (most recent call last):
...
Exception: Title too short (at least 8 chars)
>>> rep.title = 'Report_1'
>>> rep.finish('Curly')

Finally we're reach the next state
>>> rep.state.title
'Complete'

The report's history holds the successful transitions so far:
>>> rep.history
['Larry: prepare', 'Curly: finish']

>>> rep.submit('Curly')

Moe objects to something in the report and sends it back to the 'Ready' state
>>> rep.reject('Moe')
>>> rep.state.title
'Ready'

Larry makes a change and resubmits:
>>> rep.content = 'foo bar'
>>> rep.finish('Larry')
>>> rep.submit('Larry')

Moe mistakenly tries to apply the `finish` transition, but that's not allowed
from the 'submitted' state:
>>> rep.finish('Moe')
Traceback (most recent call last):
...
xworkflows.base.InvalidTransitionError: Transition 'finish' isn't available from state 'submitted'.

Finally, the `approval` transition moves the report in the final state:
>>> rep.approve('Moe')
>>> rep.history
['Larry: prepare', 'Curly: finish', 'Curly: submit', 'Moe: reject', 'Larry: finish', 'Larry: submit', 'Moe: approve']
"""

from functools import wraps

import logging
import structlog

from xworkflows import (
    Workflow,
    WorkflowEnabled,
    transition,
    before_transition,
    on_enter_state,
    after_transition,
)

logging.basicConfig(level=logging.WARNING, format='%(message)s')
log = structlog.get_logger()


def nolog(*args, **kwargs):
    """Used for disabling logging during doctest"""
    pass


class ReportWorkflow(Workflow):
    # A list of state names
    states = (
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('complete', 'Complete'),
        ('submitted', 'Submitted'),
        ('done', 'Done'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    )

    # A list of transition definitions; items are (name, source states, target).
    transitions = (
        ('prepare', 'draft', 'ready'),
        ('finish', 'ready', 'complete'),
        ('submit', 'complete', 'submitted'),
        ('approve', 'submitted', 'approved'),
        ('reject', 'submitted', 'ready'),
        ('cancel', ('ready', 'complete'), 'cancelled'),
    )

    initial_state = 'draft'

    def log_transition(self, *args, **kwargs):
        # Inactivate built-in transition logging
        pass


def keep_history(f):
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


def check_all(*checks):
    """Transition decorator, raises an exception if any of the checks fails."""

    def _check_all(f):
        @wraps(f)
        def wrapper(instance, *args, **kwargs):
            for check in checks:
                cond = instance.checks[check]
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
                cond = instance.checks[check]
                if not cond.verify({'doc': instance}):
                    failures.append((check, cond.error_msg))
            if len(failures) == len(checks):
                log.error('All checks failed', transition=f.__name__, checks=checks)
                raise Exception(f'All checks failed for {f.__name__}')
            else:
                return f(instance, *args, **kwargs)

        return wrapper

    return _check_any


class Check:
    def __init__(self, expr, error_msg=None):
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

    def verify(self, *args):
        """Evaluates the expression.
        Will pass locals and globals to `eval`"""
        return eval(self.expr_obj, *args)


class Report(WorkflowEnabled):
    state = ReportWorkflow()

    def __init__(self, title, content=None, keywords=None, checks=None):
        self.title = title
        self.content = content
        self.keywords = keywords or []
        self.history = []
        checks = checks or {}
        self.checks = {name: Check(*spec) for name, spec in checks.items()}

    @transition()
    @check_any('has_content', 'has_keywords')
    @keep_history
    def prepare(self, user):
        pass

    @transition()
    @check_all('has_content', 'title_size')
    @keep_history
    def finish(self, user):
        pass

    @transition()
    @keep_history
    def submit(self, user):
        pass

    @transition()
    @keep_history
    def cancel(self, user):
        pass

    @transition()
    @keep_history
    def approve(self, user):
        pass

    @transition()
    @keep_history
    def reject(self, user):
        pass

    @on_enter_state()
    def announce_state(self, *args, **kwargs):
        log.debug(f'{self.title}', evt='state_change', state=self.state.title, history=self.history)

    @before_transition()
    def notify_transition_start(self, *args, **kwargs):
        log.debug(f'{self.title}', evt='transition_start', from_state=self.state.title)

    @after_transition()
    def notify_transition_end(self, *args, **kwargs):
        log.debug(f'{self.title}', evt='transition_end', to_state=self.state.title)


if __name__ == '__main__':
    import doctest

    doctest.testmod()
