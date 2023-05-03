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
from itertools import cycle

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
    display_title = String(
        display_name="Display Title",
        help="Display title for this module",
        default="",
        scope=Scope.settings,
    )
    id_content = Integer(
        display_name="Id Content",
        help="Indica cual es el contenido que se va a aprobar",
        default=0,
        scope=Scope.settings,
    )
    id_institution = Integer(
        display_name="Id Content",
        help="Indica la id de la institucion",
        default=3093,
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

    def check_settings(self):
        return (is_empty(DJANGO_SETTINGS.CORFOGENERATE_URL_TOKEN) or
            is_empty(DJANGO_SETTINGS.CORFOGENERATE_CLIENT_ID) or
            is_empty(DJANGO_SETTINGS.CORFOGENERATE_CLIENT_SECRET) or
            is_empty(DJANGO_SETTINGS.CORFOGENERATE_URL_VALIDATE))

    def author_view(self, context=None):
        context = {'xblock': self, 'location': str(
            self.location).split('@')[-1]}
        context['status_settings'] = self.check_settings()
        template = self.render_template(
            'static/html/author_view.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/corfogeneratecode.css"))
        return frag

    def studio_view(self, context):
        """
        Render a form for editing this XBlock
        """
        from .models import CorfoCodeMappingContent, CorfoCodeInstitution
        fragment = Fragment()

        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'list_content': CorfoCodeMappingContent.objects.all().values('id_content', 'content'),
            'list_institution': CorfoCodeInstitution.objects.all().values('id_institution', 'institution')
        }
        context['len_list_institution'] = len(context['list_institution'])
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
        frag.initialize_js('CorfoGenerateXBlock')
        return frag

    def get_context(self):
        data = self.get_corfo_user_data()
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'passed': self.user_course_passed(),
            'code': data['code'],
            'user_rut': self.get_user_rut(),
            'corfo_save': data['corfo_save'],
            'status_settings': self.check_settings()
        }
        return context

    def get_user_rut(self):
        """
            Get user data from EdxLoginUser model
        """
        from .models import CorfoCodeUser
        from django.contrib.auth.models import User
        if CorfoCodeUser.objects.filter(user=self.scope_ids.user_id, mapping_content__id_content=self.id_content).exists():
            corfouser = CorfoCodeUser.objects.get(user=self.scope_ids.user_id, mapping_content__id_content=self.id_content)
            user = corfouser.user
            aux_run = corfouser.rut
        else:
            user = User.objects.get(id=self.scope_ids.user_id)
            aux_run = ''
        try:
            if aux_run == '':
                aux_run = user.edxloginuser.run
            if aux_run[0] == 'P':
                return aux_run
            elif aux_run[0].isalpha():
                return ''
            else:
                run = str(int(aux_run[:-1])) + aux_run[-1]
                return run
        except (AttributeError, ValueError) as e:
            return ''

    def get_corfo_user_data(self):
        from .models import CorfoCodeUser
        try:
            corfouser = CorfoCodeUser.objects.get(user=self.scope_ids.user_id, mapping_content__id_content=self.id_content)
            return {'code': corfouser.code, 'corfo_save': corfouser.corfo_save}
        except CorfoCodeUser.DoesNotExist:
            return {'code': '', 'corfo_save': False}

    def user_course_passed(self):
        from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=self.scope_ids.user_id)
            response = CourseGradeFactory().read(user, course_key=self.course_id)
            return response.passed
        except User.DoesNotExist:
            return False

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        try:
            if not self.validate_content(int(data.get('id_content', '0')), data.get('content', ''), int(data.get('id_institution', '3093'))):
                return {'result': 'error'}
            self.display_name = data.get('display_name') or self.display_name.default
            self.display_title = data.get('display_title', '')
            self.id_content = int(data.get('id_content', '0'))
            self.id_institution = int(data.get('id_institution', '3093'))
            self.content = data.get('content', '')
            return {'result': 'success'}
        except ValueError:
            #if id_content type is not Integer            
            return {'result': 'error'}

    @XBlock.json_handler
    def generate_code(self, data, suffix=''):
        from .views import generate_code
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=self.scope_ids.user_id)
            response = generate_code(user, str(self.course_id), self.id_institution, self.id_content)
            return response
        except User.DoesNotExist:
            return {'result':'error', 'status': 5, 'message': 'Usuario no ha iniciado sesión, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}

    @XBlock.json_handler
    def generate_code_rut(self, data, suffix=''):
        from .views import generate_code
        from django.contrib.auth.models import User
        user_rut = data.get('user_rut', '')
        if user_rut == '':
            return {'result':'error', 'status': 8, 'message': 'Debe incluir rut o pasaporte para generar el código.'}
        user_rut = user_rut.upper()
        user_rut = user_rut.replace("-", "")
        user_rut = user_rut.replace(".", "")
        user_rut = user_rut.strip()
        if user_rut[0] == 'P':
            if 5 > len(user_rut[1:]) or len(user_rut[1:]) > 20:
                return {'result':'error', 'status': 9, 'message': 'El pasaporte {} no es válido.'.format(user_rut)}
        else:
            if not self.validarRut(user_rut):
                return {'result':'error', 'status': 10, 'message': 'El rut {} no es válido.'.format(user_rut)}
        try:
            user = User.objects.get(id=self.scope_ids.user_id)
            response = generate_code(user, str(self.course_id), self.id_institution, self.id_content, user_rut)
            return response
        except User.DoesNotExist:
            return {'result':'error', 'status': 5, 'message': 'Usuario no ha iniciado sesión, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}

    def validarRut(self, rut):
        """
            Verify if the 'rut' is valid
        """
        try:
            rut = rut.upper()
            rut = rut.replace("-", "")
            rut = rut.replace(".", "")
            rut = rut.strip()
            aux = rut[:-1]
            dv = rut[-1:]

            revertido = list(map(int, reversed(str(aux))))
            factors = cycle(list(range(2, 8)))
            s = sum(d * f for d, f in zip(revertido, factors))
            res = (-s) % 11

            if str(res) == dv:
                return True
            elif dv == "K" and res == 10:
                return True
            else:
                print('asdasdasdasdas')
                return False
        except Exception as e:
            print(str(e))
            log.info('CorfoGenerateXBlock - Error validarRut, rut: {}'.format(rut))
            return False

    def validate_content(self, id_cont, cont, id_institution):
        from .models import CorfoCodeMappingContent, CorfoCodeInstitution
        try:
            corfomapping = CorfoCodeMappingContent.objects.get(id_content=id_cont, content=cont)
            if id_institution != 3093:
                institution = CorfoCodeInstitution.objects.get(id_institution=id_institution)
            return True
        except (CorfoCodeMappingContent.DoesNotExist, CorfoCodeInstitution.DoesNotExist) as e:
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

def is_empty(attr):
    """
        check if attribute is empty or None
    """
    return attr == "" or attr == 0 or attr is None