from functools import wraps

import structlog
from xworkflows import (
    Workflow,
    WorkflowEnabled,
    transition,
    before_transition,
    on_enter_state,
    after_transition,
)

log = structlog.get_logger()

KEEP_HISTORY = True


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


class Report(WorkflowEnabled):
    state = ReportWorkflow()

    def __init__(self, title, content):
        self.title = title
        self.content = content
        self.history = []

    @transition()
    @keep_history
    def prepare(self, user):
        pass

    @transition()
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
    rep1 = Report(title='Report1', content='foo')

    rep1.prepare('Larry')
    rep1.finish('Curly')
    rep1.cancel('Curly')

    rep2 = Report(title='Report2', content='foo')

    rep2.prepare('Larry')
    rep2.finish('Curly')
    rep2.submit('Curly')
    rep2.reject('Moe')
    rep2.finish('Larry')
    rep2.submit('Larry')
    rep2.approve('Moe')
