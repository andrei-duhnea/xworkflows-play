"""
Xworkflows's API allows creating custom workflow declaratively,
by specifying the states and transitions in a class that inherits
from `xworkflows.Workflow` to produce a workflow class factory.

This module provides the helper function `make_workflow`, that
can produce such workflow class factories.
The main use case is building workflows dynamically, at runtime,
by sourcing the states and transitions from a storage backend
like a config file or database.

Here we declare the states and transitions rather than loading them
from a data source, but the point is they're outside a workflow class definition.
>>> states = (
...    ('draft', 'Draft'),
...    ('ready', 'Ready'),
...    ('complete', 'Complete'),
...    ('submitted', 'Submitted'),
...    ('done', 'Done'),
...    ('approved', 'Approved'),
...    ('cancelled', 'Cancelled'),
... )
>>> transitions = (
...     ('prepare', 'draft', 'ready'),
...     ('finish', 'ready', 'complete'),
...     ('submit', 'complete', 'submitted'),
...     ('approve', 'submitted', 'approved'),
...     ('reject', 'submitted', 'ready'),
...     ('cancel', ('ready', 'complete'), 'cancelled'),
... )
>>> initial_state = 'draft'

The helper factory will produce the meta class that can build our custom workflow:
>>> MyWorkFlow = make_workflow('MyWorkFlow', states, transitions, initial_state)
>>> MyWorkFlow.__class__
<class 'xworkflows.base.WorkflowMeta'>

The custom metaclass builds the actual workflow class:
>>> wf = MyWorkFlow()
>>> wf.__class__
<class 'xworkflows.base.MyWorkFlow'>

Our states and transitions are now proper XWorkflows objects.
>>> wf.states #doctest: +ELLIPSIS
StateList({'draft': <State: 'draft'>, 'ready': <State: 'ready'>, ..., 'cancelled': <State: 'cancelled'>})
>>> wf.transitions #doctest: +ELLIPSIS
TransitionList(dict_values([Transition('prepare', [<State: 'draft'>], <State: 'ready'>), ...]))
>>> wf.initial_state
<State: 'draft'>
"""

import json
from xworkflows import Workflow


def make_workflow(name, states, transitions, initial_state, log_transitions=False):
    """
    A workflow (meta) class factory.
    """

    # noinspection PyUnusedLocal
    def dont_log_transition(self, *args, **kwargs):
        pass

    bases = (Workflow,)
    attrs = {
        'states': states,
        'transitions': transitions,
        'initial_state': initial_state
    }

    if not log_transitions:
        attrs.update({'log_transition': dont_log_transition})

    return type(name, bases, attrs)


def load_json_workflows(json_file):
    with open(json_file) as fd:
        wf_specs = json.load(fd)
        workflows = {}
        for wf, spec in wf_specs.items():
            states = ((s['name'], s['title']) for s in spec['states'])
            transitions = ((t['name'], t['sources'], t['target']) for t in spec['transitions'])
            initial_state = spec['initial_state']
            workflows[wf] = make_workflow(name=wf, states=states, transitions=transitions, initial_state=initial_state)
        return workflows


if __name__ == '__main__':
    import doctest
    doctest.testmod()
