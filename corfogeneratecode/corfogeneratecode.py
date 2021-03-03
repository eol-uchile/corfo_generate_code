import pkg_resources
import six
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request

import logging
from six import text_type
from django.conf import settings as DJANGO_SETTINGS
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String, Dict, Float, Boolean, List, DateTime, JSONField
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from xblockutils.resources import ResourceLoader
from django.template import Context, Template
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from django.http import Http404, HttpResponse
from django.urls import reverse


log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)
# Make '_' a no-op so we can scrape strings


def _(text): return text


def reify(meth):
    """
    Decorator which caches value so it is only computed once.
    Keyword arguments:
    inst
    """
    def getter(inst):
        """
        Set value to meth name in dict and returns value.
        """
        value = meth(inst)
        inst.__dict__[meth.__name__] = value
        return value
    return property(getter)


class CorfoGenerateXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        display_name="Display Name",
        help="Display name for this module",
        default="Corfo Generate Code",
        scope=Scope.settings,
    )
    id_content = Integer(
        display_name="Id Content",
        help="Indica cual es el contenido que se va a aprobar",
        default=0,
        scope=Scope.settings,
    )
    content = String(
        display_name="Content",
        help="Nombre del contenido impartido, según la malla de 'El viaje del Emprendedor'",
        default="",
        scope=Scope.settings,
    )
    has_author_view = True
    has_score = False
    editable_fields = ('display_name', 'id_content', 'content')

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    @reify
    def block_course_id(self):
        """
        Return the course_id of the block.
        """
        return six.text_type(self.course_id)

    @reify
    def block_id(self):
        """
        Return the usage_id of the block.
        """
        return six.text_type(self.scope_ids.usage_id)

    def is_course_staff(self):
        # pylint: disable=no-member
        """
         Check if user is course staff.
        """
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

    def is_instructor(self):
        # pylint: disable=no-member
        """
        Check if user role is instructor.
        """
        return self.xmodule_runtime.get_user_role() == 'instructor'

    def show_staff_grading_interface(self):
        """
        Return if current user is staff and not in studio.
        """
        in_studio_preview = self.scope_ids.user_id is None
        return self.is_course_staff() and not in_studio_preview

    def author_view(self, context=None):
        context = {'xblock': self, 'location': str(
            self.location).split('@')[-1]}
        template = self.render_template(
            'static/html/author_view.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/corfogeneratecode.css"))
        return frag

    def studio_view(self, context):
        """
        Render a form for editing this XBlock
        """
        from .models import CorfoCodeMappingContent
        fragment = Fragment()

        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'list_content': CorfoCodeMappingContent.objects.all().values('id_content', 'content')
        }
        fragment.content = loader.render_django_template(
            'static/html/studio_view.html', context)
        fragment.add_css(self.resource_string("static/css/corfogeneratecode.css"))
        fragment.add_javascript(self.resource_string(
            "static/js/src/corfogeneratecode_studio.js"))
        fragment.initialize_js('CorfoGenerateXBlock')
        return fragment

    def student_view(self, context=None):
        context = self.get_context()
        template = self.render_template(
            'static/html/corfogeneratecode.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/corfogeneratecode.css"))
        frag.add_javascript(self.resource_string(
            "static/js/src/corfogeneratecode.js"))
        settings = {
            'url_get_code': reverse('corfogeneratecode:generate'),
            'course_id': str(self.course_id),
            'id_content': self.id_content,
            'content': self.content
            }
        frag.initialize_js('CorfoGenerateXBlock', json_args=settings)
        return frag

    def get_context(self):
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'passed': self.user_course_passed(),
            'code': self.get_corfo_code_user()
        }
        return context

    def get_corfo_code_user(self):
        from .models import CorfoCodeUser
        try:
            corfouser = CorfoCodeUser.objects.get(user=self.scope_ids.user_id, course=self.course_id)
            return corfouser.code
        except CorfoCodeUser.DoesNotExist:
            return ''

    def user_course_passed(self):
        from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
        from django.contrib.auth.models import User
        user = User.objects.get(id=self.scope_ids.user_id)
        response = CourseGradeFactory().read(user, course_key=self.course_id)
        return response.passed

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        try:
            if not self.validate_content(int(data.get('id_content', '0')), data.get('content', '')):
                return {'result': 'error'}
            self.display_name = data.get('display_name') or self.display_name.default
            self.id_content = int(data.get('id_content', '0'))
            self.content = data.get('content', '')
            return {'result': 'success'}
        except ValueError:
            #if id_content type is not Integer            
            return {'result': 'error'}

    def validate_content(self, id_cont, cont):
        from .models import CorfoCodeMappingContent
        try:
            corfomapping = CorfoCodeMappingContent.objects.get(id_content=id_cont, content=cont)
            return True
        except CorfoCodeMappingContent.DoesNotExist:
            return False

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("CorfoGenerateXBlock",
             """<corfogeneratecode/>
             """),
            ("Multiple CorfoGenerateXBlock",
             """<vertical_demo>
                <corfogeneratecode/>
                <corfogeneratecode/>
                <corfogeneratecode/>
                </vertical_demo>
             """),
        ]
