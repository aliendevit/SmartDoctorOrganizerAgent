"""Package bootstrap for SmartDoctorOrganizerAgent.

This package wrapper ensures the project modules that live at the
repository root remain importable via the ``SmartDoctorOrganizerAgent``
package namespace.  By appending the repository root to ``__path__`` we
allow imports such as ``SmartDoctorOrganizerAgent.utils`` or
``SmartDoctorOrganizerAgent.main`` to resolve without requiring the
project to be installed as a site package.
"""
from __future__ import annotations

from pathlib import Path

# When the package is imported, ``__path__`` already contains the
# directory for ``SmartDoctorOrganizerAgent``.  We extend it with the
# repository root so that submodules located next to this package (for
# example ``utils`` or ``main``) can still be resolved as package
# imports.
_project_root = Path(__file__).resolve().parent.parent
_root_str = str(_project_root)
if _root_str not in __path__:
    __path__.append(_root_str)

del _project_root, _root_str
