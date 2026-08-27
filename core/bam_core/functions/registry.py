import importlib
import inspect
import pkgutil
from typing import Type

from bam_core.functions.base import Function


def list_function_module_names() -> list[str]:
    """
    Return all module names available under bam_core.functions,
    excluding internal/support modules.
    """
    package = importlib.import_module("bam_core.functions")
    names = []
    for module_info in pkgutil.iter_modules(package.__path__):
        name = module_info.name
        if name.startswith("_") or name in {"base", "params", "registry"}:
            continue
        names.append(name)
    return sorted(names)


def resolve_function_class(function_name: str) -> Type[Function]:
    """
    Resolve a Function subclass from a module name under bam_core.functions.
    Raises ValueError if the module or class cannot be found.
    """
    module_name = function_name.strip().lower().replace("-", "_")
    if not module_name:
        raise ValueError("Function name is required")

    try:
        module = importlib.import_module(f"bam_core.functions.{module_name}")
    except ModuleNotFoundError:
        raise ValueError(f"Function '{function_name}' not found")

    for _, cls in inspect.getmembers(module, inspect.isclass):
        if (
            issubclass(cls, Function)
            and cls is not Function
            and cls.__module__ == module.__name__
        ):
            return cls

    raise ValueError(
        f"No runnable Function class found for '{function_name}'"
    )


def init_function(function_name: str) -> Function:
    """
    Instantiate and return the Function for the given module name.
    Raises ValueError if the function cannot be found.
    Raises RuntimeError if instantiation fails.
    """
    fn_class = resolve_function_class(function_name)
    try:
        return fn_class()
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize function '{function_name}': {e}"
        ) from e
