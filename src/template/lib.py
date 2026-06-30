__all__ = ["TEMPLATE", "ERROR_MESSAGE", "template_func", "failing_template_func"]

TEMPLATE = "template"
ERROR_MESSAGE = "This is a template error message."


def template_func() -> bool:
    """
    This is a template function that does nothing.
    """
    return True


def failing_template_func() -> bool:
    """
    This function is supposed to fail.
    """
    raise ValueError(ERROR_MESSAGE)
