from django import forms
from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import filesizeformat

from .models import Attachment, Log, Email, EmailTemplate, STATUS
from .widgets import CommaSeparatedEmailWidget


def get_message_preview(instance):
    return Truncator(instance.message).chars(25)

get_message_preview.short_description = 'Message'


class AttachmentInline(admin.TabularInline):
    model = Attachment.emails.through
    extra = 0
    ordering = ['attachment__name']
    fields = ['attachment_file', 'attachment_filesize']
    readonly_fields = ['attachment_file', 'attachment_filesize']
    verbose_name_plural = _('Attachments')

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def attachment_file(self, instance):
        attachment = instance.attachment
        return format_html(
            '<a href="{url}">{name}</a>',
            url=attachment.file.url,
            name=attachment.name
        )

    attachment_file.short_description = _('Name')
    attachment_file.allow_tags = True

    def attachment_filesize(self, instance):
        return filesizeformat(instance.attachment.file.size)

    attachment_filesize.short_description = _('Size')


class LogInline(admin.TabularInline):
    model = Log
    extra = 0
    ordering = ['date']
    fields = ['date', 'status', 'exception_type', 'message_display']
    readonly_fields = ['date', 'status', 'exception_type', 'message_display']

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def message_display(self, instance):
        return Truncator(instance.message).chars(64)
    message_display.short_description = _('Message')


class EmailAdminForm(forms.ModelForm):
    class Meta:
        model = Email
        fields = forms.ALL_FIELDS
        widgets = {
            'to': CommaSeparatedEmailWidget,
            'cc': CommaSeparatedEmailWidget,
            'bcc': CommaSeparatedEmailWidget,
        }


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    form = EmailAdminForm
    list_display = ('id', 'to_display', 'subject', 'template',
                    'status', 'last_updated')
    search_fields = ['to', 'subject']
    date_hierarchy = 'last_updated'
    inlines = [AttachmentInline, LogInline]
    list_filter = ['status', 'template__language', 'template__name']
    actions = ['requeue']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('template')

    def to_display(self, instance):
        return ', '.join(instance.to)
    to_display.short_description = _('to')
    to_display.admin_order_field = 'to'

    def get_inline_instances(self, request, obj=None):
        """ Do not show empty readonly inlines """
        inline_instances = []
        for inline in super().get_inline_instances(request, obj):
            if isinstance(inline, AttachmentInline):
                if obj is None or not obj.attachments.exists():
                    continue
            if isinstance(inline, LogInline):
                if obj is None or not obj.logs.exists():
                    continue
            inline_instances.append(inline)
        return inline_instances

    def requeue(self, request, queryset):
        """An admin action to requeue emails."""
        queryset.update(status=STATUS.queued)
    requeue.short_description = _('Requeue selected emails')


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('date', 'email', 'status', get_message_preview)


class EmailTemplateAdminFormSet(BaseInlineFormSet):
    def clean(self):
        """
        Check that no two Email templates have the same default_template and language.
        """
        super().clean()
        data = set()
        for form in self.forms:
            default_template = form.cleaned_data['default_template']
            language = form.cleaned_data['language']
            if (default_template.id, language) in data:
                msg = _("Duplicate template for language '{language}'.")
                language = dict(form.fields['language'].choices)[language]
                raise ValidationError(msg.format(language=language))
            data.add((default_template.id, language))


class EmailTemplateAdminForm(forms.ModelForm):
    language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        required=False,
        label=_("Language"),
        help_text=_("Render template in alternative language"),
    )

    class Meta:
        model = EmailTemplate
        fields = ['name', 'description', 'subject', 'content', 'html_content', 'language',
                  'default_template']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.language:
            self.fields['language'].disabled = True


class EmailTemplateInline(admin.StackedInline):
    form = EmailTemplateAdminForm
    formset = EmailTemplateAdminFormSet
    model = EmailTemplate
    extra = 0
    fields = ('language', 'subject', 'content', 'html_content',)

    def get_max_num(self, request, obj=None, **kwargs):
        return len(settings.LANGUAGES)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateAdminForm
    list_display = ('name', 'description_shortened', 'subject', 'languages_compact', 'created')
    search_fields = ('name', 'description', 'subject')
    fieldsets = [
        (None, {
            'fields': ('name', 'description'),
        }),
        (_("Default Content"), {
            'fields': ('subject', 'content', 'html_content'),
        }),
    ]
    inlines = (EmailTemplateInline,) if settings.USE_I18N else ()

    def get_queryset(self, request):
        return self.model.objects.filter(default_template__isnull=True)

    def description_shortened(self, instance):
        return Truncator(instance.description.split('\n')[0]).chars(200)
    description_shortened.short_description = _("Description")
    description_shortened.admin_order_field = 'description'

    def languages_compact(self, instance):
        languages = [tt.language for tt in instance.translated_templates.order_by('language')]
        return ', '.join(languages)
    languages_compact.short_description = _("Languages")

    def save_model(self, request, obj, form, change):
        obj.save()

        # if the name got changed, also change the translated templates to match again
        if 'name' in form.changed_data:
            obj.translated_templates.update(name=obj.name)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'file', )
