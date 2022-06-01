from traitlets import Int, Float

__all__ = ['HandleEmptyMixin', 'IntHandleEmpty', 'FloatHandleEmpty']


class HandleEmptyMixin:
    """Mixin to handle empty field."""
    def __init__(self, *args, **kwargs):
        self._empty_to_default = kwargs.pop('replace_with_default', False)
        super().__init__(*args, **kwargs)

    def validate(self, obj, value):
        if value is None or (isinstance(value, str) and not len(value)):
            if self._empty_to_default:
                # If the field is emptied, it will override with the default value.
                return self.default_value
            # The value will remain as the empty string or None, likely will need to either
            # couple this with form validation or handle the case where the value
            # is an empty string once retrieved.
            return value
        return super().validate(obj, value)


class IntHandleEmpty(HandleEmptyMixin, Int):
    """Mixin to handle empty integer field."""
    pass


class FloatHandleEmpty(HandleEmptyMixin, Float):
    """Mixin to handle empty floating point field."""
    def validate(self, obj, value):
        if value == '.':
            return value
        return super().validate(obj, value)
