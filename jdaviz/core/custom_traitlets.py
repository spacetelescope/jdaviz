from traitlets import Int, Float


class HandleEmptyMixin(object):
    def __init__(self, *args, **kwargs):
        self._empty_to_default = kwargs.pop('replace_with_default', False)
        super().__init__(*args, **kwargs)

    def validate(self, obj, value):
        if isinstance(value, str) and not len(value):
            if self._empty_to_default:
                # if the field is emptied, it will override with the default value
                return self.default_value
            # the value will remain as the empty string, likely will need to either
            # couple this with form validation or handle the case where the value
            # is an empty string once retrieved.
            return value
        return super().validate(obj, value)


class IntHandleEmpty(HandleEmptyMixin, Int):
    pass


class FloatHandleEmpty(HandleEmptyMixin, Float):
    pass
