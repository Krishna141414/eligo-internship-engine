"""Eligo shared ML core.

Imported by both the Jupyter notebook (training, evaluation, artifact export)
and the Django app (inference only). Keeping one copy of this logic is what
guarantees the notebook and the web app compute the same thing.
"""

__version__ = "1.0.0"
