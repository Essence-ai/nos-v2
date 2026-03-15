"""
NeuronOS VM Manager

Manages the Windows VM lifecycle and provides seamless application integration.
"""

from neuronvm.lifecycle import VMLifecycleManager
from neuronvm.looking_glass import LookingGlassWrapper
from neuronvm.app_router import AppRouter, ExecutionPath

__version__ = "0.1.0"
__all__ = [
    "VMLifecycleManager",
    "LookingGlassWrapper",
    "AppRouter",
    "ExecutionPath",
]
