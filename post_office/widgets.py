from django import forms


class CommaSeparatedEmailWidget(forms.TextInput):
    def format_value(self, value):
        if not value:
            return ''
        if isinstance(value, str):
            value = [value, ]
        return ', '.join([item for item in value])

    # Django 1.8 - 1.10 support
    _format_value = format_value
