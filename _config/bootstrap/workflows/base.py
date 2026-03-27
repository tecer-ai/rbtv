import abc
from bootstrap.context import BootstrapContext

class BootstrapWorkflow(abc.ABC):
    def __init__(self, ctx: BootstrapContext):
        self.ctx = ctx

    @abc.abstractmethod
    def run(self) -> int:
        pass
