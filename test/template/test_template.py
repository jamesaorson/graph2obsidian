import template.lib


def test_template():
    assert template.lib.template_func()
    try:
        template.lib.failing_template_func()
    except ValueError as e:
        assert str(e) == template.lib.ERROR_MESSAGE
