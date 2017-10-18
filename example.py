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

We specify checks as a list of (name, expression, error message) tuples.
The report instance will be exposed as `doc` to check locals.
>>> checks_list = [
...    ('has_content',
...     'doc.content is not None and len(doc.content) > 0',
...     'Content is empty'),
...    ('has_keywords',
...     'doc.keywords',
...     'No keywords defined'),
...    ('title_size',
...     'len(doc.title) >= 8',
...     'Title too short (at least 8 chars)')
... ]
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
    WorkflowEnabled,
    transition,
    before_transition,
    on_enter_state,
    after_transition,
)

from docflows import load_json_workflows
from docflows.transitions import keep_history
from docflows.check import Check, CheckList, check_all, check_any


logging.basicConfig(level=logging.WARNING, format='%(message)s')
log = structlog.get_logger()


def nolog(*args, **kwargs):
    """Used for disabling logging during doctest"""
    pass


workflows = load_json_workflows('workflows.json')
ReportWorkflow = workflows['ReportWorkflow']


class Report(WorkflowEnabled):
    state = ReportWorkflow()

    def __init__(self, title, content=None, keywords=None, checks=None):
        self.title = title
        self.content = content
        self.keywords = keywords or []
        self.history = []
        checks = checks or {}
        self.checks = CheckList(checks=[Check(*spec) for spec in checks])

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
