"""
Purpose:
    Analysis adapters that turn Python source into Archbrace's internal models.

Inputs:
    Source text and parsed syntax trees.

Outputs:
    Structural module models and Radon-backed metrics.

Side effects:
    None.

Failure behavior:
    Adapters raise ``ArchbraceError`` subclasses on unrecoverable parse errors.
"""
