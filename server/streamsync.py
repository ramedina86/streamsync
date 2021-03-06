import uuid
from contextlib import contextmanager
import matplotlib
import matplotlib.figure
import types
import io
import base64


def serialise(value):
    if isinstance(value, matplotlib.figure.Figure):
        fig = value
        iobytes = io.BytesIO()
        fig.savefig(iobytes, format="png")
        iobytes.seek(0)
        base64_str = base64.b64encode(iobytes.read()).decode("latin-1")
        dataurl = "data:image/png;base64," + base64_str
        matplotlib.pyplot.close(fig)
        return dataurl
    elif isinstance(value, types.FunctionType):
        return True
    elif isinstance(value, dict):
        return {k:serialise(v) for k, v in value.items()}
    else:
        return value


class StreamsyncState:


    def __init__(self):
        self.state = {}
        self.mutated = set()


    # State mutations are detected by intercepting the setter
    def __setitem__(self, key, value):
        self.state[key] = serialise(value)
        self.mutated.add(key)


    def __getitem__(self, key):
        return self.state[key]
        

    # Mutations are consumed once and cleared after that
    def mutations(self):
        mutated_state = {x:self.state[x] for x in self.mutated}
        self.mutated = set()
        return mutated_state


class ComponentManager:


    def __init__(self):
        self.components = {}
        self.status_modified = set()
        self.container_stack = []


    def get_active_container(self):
        if len(self.container_stack) > 0:
            return self.container_stack[-1]
        else:
            return None


    def add_component(self, type, content=None, handlers=None, conditioner=None):
        component_id = str(uuid.uuid4())
        entry = {
            "id": component_id,
            "type": type,
            "content": serialise(content),
            "handlers": handlers,
            "container": self.get_active_container(),
            "conditioner": conditioner
        }
        self.components[component_id] = entry
        return entry


    def is_component_active(self, id, state):
        component = self.components[id]
        if component["container"]: # If it's a child component, check that its parent is active
            if not self.is_component_active(component["container"], state):
                return False # If not active, the child is also not active
        if not component["conditioner"] or component["conditioner"](state):
            return True
        return False


    def get_active(self, state):
        active_components = {}
        for id, component in self.components.items():
            if self.is_component_active(id, state):
                active_components[id] = component
            else:
                placeholder = {
                    "id": component["id"],
                    "type": component["type"],
                    "placeholder": True,
                    "container": component["container"] if "container" in component else None
                }
                active_components[id] = placeholder
        return active_components
    

cm = ComponentManager()
initial_state = StreamsyncState()


def init_state(state_dict):
    initial_state.state = state_dict    


def get_active_components(state):
    return cm.get_active(state)



@contextmanager
def section(title = None):
    resource = cm.add_component("section", {"title": title})
    try:
        cm.container_stack.append(resource["id"])
        yield resource
    finally:
        cm.container_stack.pop()


@contextmanager
def when(conditioner):
    global active_container
    resource = cm.add_component("when", None, None, conditioner)
    try:
        cm.container_stack.append(resource["id"])
        yield resource
    finally:
        cm.container_stack.pop()


def title(text, handlers=None):
    cm.add_component("title", {"text": text}, handlers)


def slider(value, min=0, max=100, handlers=None):
    cm.add_component("slider", {"value": value, "min": min, "max": max}, handlers)


def button(text, handlers=None):
    cm.add_component("button", {"text": text}, handlers)


def text(text, handlers=None):
    cm.add_component("text", {"text": text}, handlers)


def heading(text, handlers=None):
    cm.add_component("heading", {"text": text}, handlers)


def pyplot(fig, handlers=None):
    cm.add_component("pyplot", {"figure": fig})