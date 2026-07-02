"""
Purpose:
    Analysis adapters that turn Python source into Archbrace's internal models.

Why is this in this project:
    Groups the source-to-model adapters so the rest of Archbrace depends on
    internal models rather than parsing or metric libraries directly.

Inputs:
    Source text and parsed syntax trees.

Outputs:
    Structural module models and Radon-backed metrics.

Side effects:
    None.

Failure behavior:
    Adapters raise ``ArchbraceError`` subclasses on unrecoverable parse errors.
"""
