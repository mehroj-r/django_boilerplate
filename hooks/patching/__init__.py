from .deps import add_dependencies, add_dependency, remove_dependencies, remove_dependency
from .engine import PatchEngine, PatchEngineError, PatchSpec
from .ops import FilePatcher, PatchOperationError

__all__ = [
    "FilePatcher",
    "PatchEngine",
    "PatchEngineError",
    "PatchOperationError",
    "PatchSpec",
    "add_dependencies",
    "add_dependency",
    "remove_dependencies",
    "remove_dependency",
]
