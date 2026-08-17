"""Transformation registry (apply order matters: nested alerts before tabs)."""

from __future__ import annotations

import importlib

# module name -> class name, in apply order
ORDER = [
    ("frontmatter", "FrontMatterTransformation"),
    ("callout", "CalloutTransformation"),
    ("param_placeholders", "ParamPlaceholdersTransformation"),
    ("tabs", "TabsTransformation"),
    ("filetree", "FileTreeTransformation"),
    ("gallery", "GalleryTransformation"),
    ("datafence", "DataFenceTransformation"),
    ("cards", "CardsTransformation"),
    ("fieldsdelim", "FieldsDelimTransformation"),
    ("image", "ImageTransformation"),
    ("include", "IncludeTransformation"),
    ("fencetitle", "FenceTitleTransformation"),
    ("badge", "BadgeTransformation"),
    ("eg", "ExampleTransformation"),
    ("reportonly", "ReportOnlyTransformation"),
]


def load(keys: list[str] | None = None) -> list[type]:
    """Import and return the transformation classes in apply order."""

    classes = []
    for module_name, class_name in ORDER:
        module = importlib.import_module(f"{__name__}.{module_name}")
        cls = getattr(module, class_name)
        if keys is None or cls.key in keys:
            classes.append(cls)
    return classes


def keys() -> list[str]:
    return [cls.key for cls in load()]


__all__ = ["ORDER", "load", "keys"]
