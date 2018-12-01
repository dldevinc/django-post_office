from django.test import TestCase, override_settings
from django.template.utils import InvalidTemplateEngineError
from ..models import Email, EmailTemplate
from ..settings import get_template_engine


class RenderTest(TestCase):

    def test_email_message_render(self):
        """
        Ensure Email instance with template is properly rendered.
        """
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = Email.objects.create(to=['to@example.com'], template=template,
            from_email='from@e.com', context=context)
        message = email.email_message()
        self.assertEqual(message.subject, 'Subject test')
        self.assertEqual(message.body, 'Content test')
        self.assertEqual(message.alternatives[0][0], 'HTML test')

    @override_settings(POST_OFFICE={'TEMPLATE_ENGINE': 'nothing'})
    def test_invalid_engine(self):
        self.assertRaises(InvalidTemplateEngineError, get_template_engine)

    # ======================================================
    #   Jinja2 test cases.
    #   Test cases below runs only when Jinja2 installed.
    # ======================================================

    try:
        import jinja2
    except ImportError:
        pass
    else:
        @override_settings(
            TEMPLATES=[
                {
                    'BACKEND': 'django.template.backends.jinja2.Jinja2',
                },
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                },
            ],
        )
        def test_template_engine(self):
            # If no template engine is set, template engine should default to django
            engine = get_template_engine()
            self.assertEqual(engine.name, 'django')

        @override_settings(
            TEMPLATES=[
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                },
                {
                    'BACKEND': 'django.template.backends.jinja2.Jinja2',
                },
            ],
            POST_OFFICE={
                'TEMPLATE_ENGINE': 'jinja2'
            },
        )
        def test_email_message_render_jinja2(self):
            """
            Ensure Email instance with template is properly rendered
            using Jinja2 template engine.
            """
            template = EmailTemplate.objects.create(
                subject='Subject {{ name }}',
                content='Content {{ empty|default("default") }}',
                html_content='HTML {{ range(1,4)|join(",") }}'
            )
            context = {'name': 'test'}
            email = Email.objects.create(to=['to@example.com'], template=template,
                from_email='from@e.com', context=context)
            message = email.email_message()
            self.assertEqual(message.subject, 'Subject test')
            self.assertEqual(message.body, 'Content default')
            self.assertEqual(message.alternatives[0][0], 'HTML 1,2,3')


