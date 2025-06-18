#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python Standard Libraries
from collections import namedtuple
import json

# Installed packages (via pip)
from django.test import Client
from django.test.utils import override_settings
from mock import patch, Mock, MagicMock
from uchileedxlogin.models import EdxLoginUser
import six

# Edx dependencies
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.tests.base import GradeTestBase
from lms.djangoapps.grades.tests.utils import mock_get_score
from opaque_keys.edx.keys import CourseKey
from xblock.field_data import DictFieldData

# Internal project dependencies
from .corfogeneratecode import CorfoGenerateXBlock
from .models import CorfoCodeUser, CorfoCodeMappingContent, CorfoCodeInstitution
from .views import user_course_passed, grade_percent_scaled, generate_code, validate_data, get_grade_cutoff, get_token, validate_mooc

# Create your tests here.

class TestRequest(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None

class TestCorfoGenerateXBlock(GradeTestBase):

    def make_an_xblock(cls, **kw):
        """
        Helper method that creates a CorfoGenerateXBlock
        """

        course = cls.course
        runtime = Mock(
            course_id=course.id,
            user_is_staff=False,
            service=Mock(
                return_value=Mock(_catalog={}),
            ),
        )
        scope_ids = Mock()
        field_data = DictFieldData(kw)
        xblock = CorfoGenerateXBlock(runtime, field_data, scope_ids)
        xblock.xmodule_runtime = runtime
        xblock.location = course.location
        xblock.course_id = course.id
        xblock.category = 'corfogeneratecode'
        xblock.scope_ids.usage_id = 2
        return xblock

    def setUp(self):
        super(TestCorfoGenerateXBlock, self).setUp()        
        CorfoCodeMappingContent.objects.create(id_content=200, content='testtest')
        self.grade_factory = CourseGradeFactory()
        self.xblock = self.make_an_xblock()
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.client = Client()
            user = UserFactory(
                username='testuser101',
                password='12345',
                email='student@edx.org',
                is_staff=True)
            self.client.login(username='testuser101', password='12345')
            CourseEnrollmentFactory(
                user=user, course_id=self.course.id)
            # user student
            self.student_client = Client()
            self.student = UserFactory(
                username='student',
                password='12345',
                email='student2@edx.org')
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)
            self.assertTrue(
                self.student_client.login(
                    username='student',
                    password='12345'))
            # user student2
            self.student2_client = Client()
            self.student2 = UserFactory(
                username='student2',
                password='12345',
                email='student22@edx.org')
            CourseEnrollmentFactory(
                user=self.student2, course_id=self.course.id)
            self.assertTrue(
                self.student2_client.login(
                    username='student2',
                    password='12345'))

    def test_user_course_passed(self):
        """
            Verify method user_course_passed() work correctly
        """
        with mock_get_score(1, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(1, 4):
            self.xblock.scope_ids.user_id = self.student.id
            passed = self.xblock.user_course_passed()
            self.assertFalse(passed)

    def test_user_course_passed_wrong_user_id(self):
        """
            Verify method user_course_passed with wrong user_id
        """
        self.xblock.scope_ids.user_id = '111'
        passed = self.xblock.user_course_passed()
        self.assertFalse(passed)
    
    def test_validate_field_data(self):
        """
            Verify if default xblock is created correctly
        """
        self.assertEqual(self.xblock.display_name, 'Corfo Generate Code')
        self.assertEqual(self.xblock.display_title, '')
        self.assertEqual(self.xblock.id_content, 0)
        self.assertEqual(self.xblock.id_institution, 3093)
        self.assertEqual(self.xblock.content, '')

    def test_edit_block_studio(self):
        """
            Verify submit studio edits is working
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.display_title, 'testtitle')
        self.assertEqual(self.xblock.id_content, 200)
        self.assertEqual(self.xblock.id_institution, 3093)
        self.assertEqual(self.xblock.content, 'testtest')

    def test_edit_block_studio_2(self):
        """
            Verify submit studio edits is working with CorfoCodeInstitution
        """
        CorfoCodeInstitution.objects.create(id_institution=3090, institution='NVIDIA')
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', 'id_institution': '3090', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.display_title, 'testtitle')
        self.assertEqual(self.xblock.id_content, 200)
        self.assertEqual(self.xblock.id_institution, 3090)
        self.assertEqual(self.xblock.content, 'testtest')

    def test_fail_edit_block_studio(self):
        """
            Verify submit studio edits when CorfoCodeMappingContent.DoesNotExist
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '202', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'Corfo Generate Code')
        self.assertEqual(self.xblock.display_title, '')
        self.assertEqual(self.xblock.id_content, 0)
        self.assertEqual(self.xblock.content, '')
        self.assertEqual(self.xblock.id_institution, 3093)

    def test_fail_edit_block_studio_2(self):
        """
            Verify submit studio edits when CorfoCodeInstitution.DoesNotExist
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', 'id_institution': '3000', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'Corfo Generate Code')
        self.assertEqual(self.xblock.display_title, '')
        self.assertEqual(self.xblock.id_content, 0)
        self.assertEqual(self.xblock.content, '')
        self.assertEqual(self.xblock.id_institution, 3093)

    def test_edit_block_studio_string_id_content(self):
        """
            Verify submit studio edits when id_content is not a number(Integer)
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": 'aa', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'Corfo Generate Code')
        self.assertEqual(self.xblock.display_title, '')
        self.assertEqual(self.xblock.id_content, 0)
        self.assertEqual(self.xblock.content, '')
        self.assertEqual(self.xblock.id_institution, 3093)

    def test_edit_block_studio_string_id_institution(self):
        """
            Verify submit studio edits when id_institution is not a number(Integer)
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', 'id_institution': 'asd', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'Corfo Generate Code')
        self.assertEqual(self.xblock.display_title, '')
        self.assertEqual(self.xblock.id_content, 0)
        self.assertEqual(self.xblock.content, '')
        self.assertEqual(self.xblock.id_institution, 3093)

    def test_student_view(self):
        """
            Verify context in student_view
        """
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context()
        self.assertEqual(response['passed'], False)
        self.assertEqual(response['code'], '')
        self.assertEqual(response['corfo_save'], False)
        self.assertEqual(response['user_rut'], '')

    def test_student_view_user_not_passed_course(self):
        """
            Verify context in student_view when user has not passed the course
        """
        with mock_get_score(1, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(1, 4):
            self.xblock.scope_ids.user_id = self.student.id
            response = self.xblock.get_context()
            self.assertEqual(response['passed'], False)
            self.assertEqual(response['code'], '')
            self.assertEqual(response['user_rut'], '')
            self.assertEqual(response['corfo_save'], False)

    def test_student_view_user_passed_course_without_code(self):
        """
            Verify context in student_view when user has passed the course and dont have code
        """
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            self.xblock.scope_ids.user_id = self.student.id
            response = self.xblock.get_context()
            self.assertEqual(response['passed'], True)
            self.assertEqual(response['code'], '')
            self.assertEqual(response['user_rut'], '')
            self.assertEqual(response['corfo_save'], False)

    def test_student_view_user_passed_course_with_code(self):
        """
            Verify context in student_view when user has passed the course and have code
        """
        mapp_content = CorfoCodeMappingContent.objects.get(id_content=200, content='testtest')
        corfouser = CorfoCodeUser.objects.create(user=self.student, mapping_content=mapp_content, code='U1CODASDFGH')
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            self.xblock.scope_ids.user_id = self.student.id
            self.xblock.id_content = 200
            response = self.xblock.get_context()
            self.assertEqual(response['passed'], True)
            self.assertEqual(response['code'], corfouser.code)
            self.assertEqual(response['user_rut'], corfouser.rut)
            self.assertEqual(response['corfo_save'], False)

    def test_student_view_user_passed_course_with_corfo_save(self):
        """
            Verify context in student_view when user has passed the course and have corfo_save
        """
        mapp_content = CorfoCodeMappingContent.objects.get(id_content=200, content='testtest')
        corfouser = CorfoCodeUser.objects.create(user=self.student, mapping_content=mapp_content, code='U1CODASDFGH', corfo_save=True)
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            self.xblock.scope_ids.user_id = self.student.id
            self.xblock.id_content = 200
            response = self.xblock.get_context()
            self.assertEqual(response['passed'], True)
            self.assertEqual(response['code'], corfouser.code)
            self.assertEqual(response['user_rut'], corfouser.rut)
            self.assertEqual(response['corfo_save'], True)
    
    def test_CorfoCodeMappingContent_str(self):
        """
            Test str function on model CorfoCodeMappingContent
        """
        map_content = CorfoCodeMappingContent.objects.get(id_content=200, content='testtest')
        str_map = str(map_content)
        self.assertEqual(str_map, '(200) -> testtest')

    def test_CorfoCodeInstitution_str(self):
        """
            Test str function on model CorfoCodeInstitution
        """
        CorfoCodeInstitution.objects.create(id_institution=300, institution="institution_test")
        institution = CorfoCodeInstitution.objects.get(id_institution=300,institution="institution_test")
        str_institution = str(institution)
        self.assertEqual(str_institution, '(300) -> institution_test')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_block_generate_code(self, post):
        """
            Verify generate_code() is working
        """
        EdxLoginUser.objects.create(user=self.student, run='009472337K')
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.display_title, 'testtitle')
        self.assertEqual(self.xblock.id_content, 200)
        self.assertEqual(self.xblock.id_institution, 3093)
        self.assertEqual(self.xblock.content, 'testtest')

        CorfoCodeInstitution.objects.create(id_institution=self.xblock.id_institution)
        post_data = {
                'Data': 0,
                'Message': None,
                'Status': 0,
                'Success': True
            }
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data) ,namedtuple("Request", ["status_code", "json"])(200, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            request = TestRequest()
            request.method = 'POST'
            self.xblock.xmodule_runtime.user_is_staff = False
            self.xblock.scope_ids.user_id = self.student.id
            data = json.dumps({})
            request.body = data.encode()
            response = self.xblock.generate_code(request)
            data = json.loads(response._app_iter[0].decode())
            self.assertEqual(data['result'], 'success')
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content__id_content=self.xblock.id_content)
            self.assertEqual(data['code'], corfouser.code)
            self.assertTrue(corfouser.corfo_save)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_block_generate_code_rut(self, post):
        """
            Verify generate_code_rut() is working
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.display_title, 'testtitle')
        self.assertEqual(self.xblock.id_content, 200)
        self.assertEqual(self.xblock.id_institution, 3093)
        self.assertEqual(self.xblock.content, 'testtest')

        CorfoCodeInstitution.objects.create(id_institution=self.xblock.id_institution)
        post_data = {
                'Data': 0,
                'Message': None,
                'Status': 0,
                'Success': True
            }
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data) ,namedtuple("Request", ["status_code", "json"])(200, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student2, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            request = TestRequest()
            request.method = 'POST'
            self.xblock.xmodule_runtime.user_is_staff = False
            self.xblock.scope_ids.user_id = self.student2.id
            data = json.dumps({'user_rut': '111111111'})
            request.body = data.encode()
            response = self.xblock.generate_code_rut(request)
            data = json.loads(response._app_iter[0].decode())
            self.assertEqual(data['result'], 'success')
            corfouser = CorfoCodeUser.objects.get(user=self.student2, mapping_content__id_content=self.xblock.id_content)
            self.assertEqual(data['code'], corfouser.code)
            self.assertEqual('111111111', corfouser.rut)
            self.assertTrue(corfouser.corfo_save)


    def test_block_generate_code_rut_no_rut(self):
        """
            Verify generate_code_rut() when missing user_rut params
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = self.student2.id
        data = json.dumps({})
        request.body = data.encode()
        response = self.xblock.generate_code_rut(request)
        data = json.loads(response._app_iter[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 8)
        self.assertFalse(CorfoCodeUser.objects.filter(user=self.student2).exists())

    def test_block_generate_code_rut_wrong_passport(self):
        """
            Verify generate_code_rut() when passport is wrong
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = self.student2.id
        data = json.dumps({'user_rut': 'PASDASDSADSADASDSADSADASDSADSADASDSADSADSADSADSADSADSAD'})
        request.body = data.encode()
        response = self.xblock.generate_code_rut(request)
        data = json.loads(response._app_iter[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 9)
        self.assertFalse(CorfoCodeUser.objects.filter(user=self.student2).exists())

    def test_block_generate_code_rut_wrong_rut(self):
        """
            Verify generate_code_rut() when user_rut is wrong
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = self.student2.id
        data = json.dumps({'user_rut': '123456'})
        request.body = data.encode()
        response = self.xblock.generate_code_rut(request)
        data = json.loads(response._app_iter[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 10)
        self.assertFalse(CorfoCodeUser.objects.filter(user=self.student2).exists())
    
    def test_block_generate_code_rut_wrong_rut_2(self):
        """
            Verify generate_code_rut() when user_rut is not a 'rut'
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = self.student2.id
        data = json.dumps({'user_rut': 'fghsdfhdfh'})
        request.body = data.encode()
        response = self.xblock.generate_code_rut(request)
        data = json.loads(response._app_iter[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 10)
        self.assertFalse(CorfoCodeUser.objects.filter(user=self.student2).exists())
    
    def test_block_generate_code_user_doesnt_exist(self):
        """
            Verify generate_code_rut() when user doesn't exist
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = '111111111'
        data = json.dumps({'user_rut': '111111111'})
        request.body = data.encode()
        response = self.xblock.generate_code_rut(request)
        data = json.loads(response._app_iter[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)
        self.assertFalse(CorfoCodeUser.objects.filter(user=self.student2).exists())
    
    def test_validarrut(self):
        """
            Verify validarRut() when the verification digit is a k
        """
        result = self.xblock.validarRut('9288743-k')
        self.assertTrue(result)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_block_generate_code_with_passport(self, post):
        """
            Verify generate_code() is working whern user have passport
        """
        EdxLoginUser.objects.create(user=self.student, run='P009472337K')
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.display_title, 'testtitle')
        self.assertEqual(self.xblock.id_content, 200)
        self.assertEqual(self.xblock.id_institution, 3093)
        self.assertEqual(self.xblock.content, 'testtest')

        CorfoCodeInstitution.objects.create(id_institution=self.xblock.id_institution)
        post_data = {
                'Data': 0,
                'Message': None,
                'Status': 0,
                'Success': True
            }
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data) ,namedtuple("Request", ["status_code", "json"])(200, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            request = TestRequest()
            request.method = 'POST'
            self.xblock.xmodule_runtime.user_is_staff = False
            self.xblock.scope_ids.user_id = self.student.id
            data = json.dumps({})
            request.body = data.encode()
            response = self.xblock.generate_code(request)
            data = json.loads(response._app_iter[0].decode())
            self.assertEqual(data['result'], 'success')
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content__id_content=self.xblock.id_content)
            self.assertEqual(data['code'], corfouser.code)
            self.assertTrue(corfouser.corfo_save)
    
    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_block_generate_code_no_passport(self, post):
        """
            Verify generate_code() is working
        """
        EdxLoginUser.objects.create(user=self.student, run='CA009472337K')
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "id_content": '200', "content": 'testtest', 'display_title': 'testtitle'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.display_title, 'testtitle')
        self.assertEqual(self.xblock.id_content, 200)
        self.assertEqual(self.xblock.id_institution, 3093)
        self.assertEqual(self.xblock.content, 'testtest')

        CorfoCodeInstitution.objects.create(id_institution=self.xblock.id_institution)
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data) ,]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            request = TestRequest()
            request.method = 'POST'
            self.xblock.xmodule_runtime.user_is_staff = False
            self.xblock.scope_ids.user_id = self.student.id
            data = json.dumps({})
            request.body = data.encode()
            response = self.xblock.generate_code(request)
            data = json.loads(response._app_iter[0].decode())
            self.assertEqual(data['result'], 'error')
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content__id_content=self.xblock.id_content)
            self.assertTrue('code' not in data)
            self.assertFalse(corfouser.corfo_save)

    def test_block_generate_code_wrong_user_id(self):
        """
            Verify generate_code() with wrong user_id 
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = '1111'
        data = json.dumps({})
        request.body = data.encode()
        response = self.xblock.generate_code(request)
        data_response = json.loads(response._app_iter[0].decode())
        expected_response = {'result':'error', 'status': 5, 'message': 'Usuario no ha iniciado sesión, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}
        self.assertEqual(data_response,expected_response)

    def test_author_view_render(self):
        """
            Check if xblock author template loaded correctly
        """
        author_view = self.xblock.author_view()
        author_view_html = author_view.content
        self.assertIn(' class="corfogeneratecode_block"', author_view_html)
    
    def test_student_view_render(self):
        """
            Check if xblock template student loaded correctly
        """
        self.xblock.scope_ids.user_id = self.student.id
        student_view = self.xblock.student_view()
        student_view_html = student_view.content
        self.assertIn('class="corfogeneratecode_block"', student_view_html)

    def test_studio_view_render(self,):
        """
            Check if xblock studio template loaded correctly
        """
        studio_view = self.xblock.studio_view(None)
        studio_view_html = studio_view.content
        self.assertIn('id="settings-tab"', studio_view_html)
    
    def test_block_course_id(self):
        """
            Check if property block_course_id is working properly
        """
        result = self.xblock.block_course_id
        self.assertEqual(result, six.text_type(self.course.id))
    
    def test_block_id(self):
        """
            Check if property block_id is working properly
        """
        result = self.xblock.block_id
        self.assertEqual(result, six.text_type(self.xblock.scope_ids.usage_id))
    
    def test_workbench_scenarios(self):
        """
        Checks workbench scenarios title and basic scenario
        """
        result_title = 'CorfoGenerateXBlock'
        basic_scenario = "<corfogeneratecode/>"
        test_result = self.xblock.workbench_scenarios()
        self.assertEqual(result_title, test_result[0][0])
        self.assertIn(basic_scenario, test_result[0][1])

    def test_get_user_rut(self):
        """
            Verify get_user_rut() is working with valid rut
        """
        EdxLoginUser.objects.create(user=self.student, run='47073090')
        id_content = 200
        mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
        CorfoCodeUser.objects.create(user=self.student, mapping_content=mapp_content, code='U1CODASDFGH', corfo_save=True)
        self.xblock.scope_ids.user_id = self.student.id
        self.xblock.id_content =id_content
        response = self.xblock.get_user_rut()
        self.assertEqual(response,'47073090')

    def test_get_user_rut_passport(self):
        """
            Verify get_user_rut() is working when user have passport
        """
        EdxLoginUser.objects.create(user=self.student, run='P009472337K')
        id_content = 200
        mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
        CorfoCodeUser.objects.create(user=self.student, mapping_content=mapp_content, code='U1CODASDFGH', corfo_save=True)
        self.xblock.scope_ids.user_id = self.student.id
        self.xblock.id_content =id_content
        response = self.xblock.get_user_rut()
        self.assertEqual(response,'P009472337K')
    
    def test_get_user_rut_not_valid_rut(self):
        """
            Verify generate_code() is working whern user have passport
        """
        EdxLoginUser.objects.create(user=self.student, run='N009472337K')
        id_content = 200
        mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
        CorfoCodeUser.objects.create(user=self.student, mapping_content=mapp_content, code='U1CODASDFGH', corfo_save=True)
        self.xblock.scope_ids.user_id = self.student.id
        self.xblock.id_content =id_content
        response = self.xblock.get_user_rut()
        self.assertEqual(response,'')

class TestCorfoGenerateView(GradeTestBase):

    def setUp(self):
        super(TestCorfoGenerateView, self).setUp()        

        self.grade_factory = CourseGradeFactory()
        CorfoCodeMappingContent.objects.create(id_content=200, content='testtest')
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.client = Client()
            user = UserFactory(
                username='testuser102',
                password='12345',
                email='student1@edx.org',
                is_staff=True)
            self.client.login(username='testuser102', password='12345')
            CourseEnrollmentFactory(
                user=user, course_id=self.course.id)
            # user no enrolled
            self.user_unenroll = UserFactory(
                username='testuser404',
                password='12345',
                email='student404@edx.org',
                is_staff=True)
            self.client_unenroll = Client()
            self.client_unenroll.login(username='testuser404', password='12345')
            # user student
            self.student_client = Client()
            self.student = UserFactory(
                username='student2',
                password='12345',
                email='student2@edx.org')
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)
            self.assertTrue(
                self.student_client.login(
                    username='student2',
                    password='12345'))

    def test_user_course_passed(self):
        """
            Verify method user_course_passed works correctly
        """
        with mock_get_score(1, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(1, 4):
            passed, percent = user_course_passed(self.student, self.course.id)
            self.assertEqual(percent, 0.25)
            self.assertFalse(passed)
    
    def test_user_course_passed_wrong_course_key(self):
        """
            Verify method user_course_passed works correctly with wrong data
        """
        with patch('corfogeneratecode.views.CourseGradeFactory') as mock_factory_class:
            mock_factory_instance = mock_factory_class.return_value
            mock_factory_instance.read.return_value = None
            passed, percent = user_course_passed(self.student, 'org.0/course_111/Run_0')
            self.assertIsNone(percent)
            self.assertIsNone(passed)

    def test_round_half_up(self):
        """
            Verify method grade_percent_scaled() work correctly
        """
        grades = [1,1.1,1.1,1.2,1.2,1.3,1.3,1.4,1.4,1.5,1.5,1.6,1.6,1.7,1.7,1.8,1.8,1.9,1.9,2,2,2.1,2.1,2.2,2.2,2.3,2.3,2.4,2.4,2.5,2.5,2.6,2.6,2.7,2.7,2.8,2.8,2.9,2.9,3,3,3.1,3.1,3.2,3.2,3.3,3.3,3.4,3.4,3.5,3.5,3.6,3.6,3.7,3.7,3.8,3.8,3.9,3.9,4,4,4.1,4.2,4.2,4.3,4.4,4.5,4.5,4.6,4.7,4.8,4.8,4.9,5,5.1,5.1,5.2,5.3,5.4,5.4,5.5,5.6,5.7,5.7,5.8,5.9,6,6,6.1,6.2,6.3,6.3,6.4,6.5,6.6,6.6,6.7,6.8,6.9,6.9,7]
        for i in range(101):
            self.assertEqual(grade_percent_scaled(i/100,0.6), grades[i])

    def test_get_grade_cutoff(self):
        """
            Verify method get_grade_cutoff() with wrong course_key
        """
        course_key = CourseKey.from_string('org.0/course_111/Run_0')
        result = get_grade_cutoff(course_key)
        self.assertIsNone(result)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_validate_data_anonymous_client(self):
        """
            Verify method validate_data works correctly with anonymous_client
        """
        anonymous_client = Client()
        anonymous_client.is_anonymous = True
        self.assertFalse(validate_data(anonymous_client,self.course.id,'111','1111'))

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_validate_data_content_0(self):
        """
            Verify method validate_data works correctly with content_0
        """
        self.client.is_anonymous = False
        self.assertFalse(validate_data(self.client,self.course.id,'111','0'))

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_generate_code_request(self):
        """
            test views.generate_code(request) without user data
        """

        data = generate_code(self.student, str(self.course.id), 3093, 200)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 0)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_generate_code_request_user_with_code(self):
        """
            test views.generate_code(request) when user already have code
        """
        id_content = 200
        mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
        corfouser = CorfoCodeUser.objects.create(user=self.student, mapping_content=mapp_content, code='U1CODASDFGH', corfo_save=True)
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'success')
            self.assertEqual(data['code'], corfouser.code)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_request_fail_token(self, post):
        """
            test views.generate_code(request) when get toket failed
        """
        id_content = 200
        post.side_effect = [namedtuple("Request", ["status_code"])(400)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 1)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_request_user_no_rut(self, post):
        """
            test views.generate_code(request) when user dont have edxloginuser.rut
        """
        id_content = 200
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 2)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_request_user_no_passport(self, post):
        """
            test views.generate_code(request) when user dont have rut or passport
        """
        EdxLoginUser.objects.create(user=self.student, run='CA09472337K')
        id_content = 200
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 2)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_request_user_wrong_rut(self, post):
        """
            test views.generate_code(request) when user have wrong edxloginuser.rut
        """
        EdxLoginUser.objects.create(user=self.student, run='0947P2337K')
        id_content = 200
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data), namedtuple("Request", ["status_code", "json"])]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 2)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_request_validate_fail(self, post):
        """
            test views.generate_code(request) when post validate failed
        """
        
        EdxLoginUser.objects.create(user=self.student, run='009472337K')

        
        id_content = 200
        post_data = {
                'Data': 0,
                'Message': None,
                'Status': 0,
                'Success': True
            }
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data), namedtuple("Request", ["status_code", "json", 'text'])(400, lambda:post_data,'error')]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 3)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_request_validate_wrong_data(self, post):
        """
            test views.generate_code(request) when post validate with wrong data
        """
        
        EdxLoginUser.objects.create(user=self.student, run='009472337K')


        id_content = 200
        post_data = {
                'Data': None,
                'Message': 'asdfgh',
                'Status': -4,
                'Success': False
            }
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data), namedtuple("Request", ["status_code", "json", 'text'])(200, lambda:post_data, 'error')]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 4)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_generate_code_request_wrong_course(self):
        """
            test views.generate_code(request) wrong course
        """
        id_content = 200

        data = generate_code(self.student, 'asd', 3093, id_content)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_generate_code_request_wrong_id_institution(self):
        """
            test views.generate_code(request) wrong id_institution
        """
        id_content = 200

        data = generate_code(self.student, str(self.course.id), 3090, id_content)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_generate_code_request_wrong_id_institution_string(self):
        """
            test views.generate_code(request) wrong id_institution
        """
        id_content = 200

        data = generate_code(self.student, str(self.course.id), 'asd', id_content)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_generate_code_request_no_id_content(self):
        """
            test views.generate_code(request) without id_content
        """
        id_content = ''

        data = generate_code(self.student, str(self.course.id), 3093, id_content)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    def test_generate_code_request_no_mapping(self):
        """
            test views.generate_code(request) when CorfoCodeMappingContent.DoesNotExist
        """
        id_content = 404

        data = generate_code(self.student, str(self.course.id), 3093, id_content)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)
    
    @override_settings(CORFOGENERATE_URL_TOKEN="")
    @override_settings(CORFOGENERATE_CLIENT_ID="")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="")
    @override_settings(CORFOGENERATE_URL_VALIDATE="")
    def test_generate_code_request_no_settings(self):
        """
            test views.generate_code(request) when settings no configurate
        """
        id_content = 200

        data = generate_code(self.student, str(self.course.id), 3093, id_content)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch("corfogeneratecode.views.user_course_passed")
    def test_generate_code_request_passed_none(self, passed):
        """
            test views.generate_code(request) when get user_course_passed failed
        """
        passed.return_value = None, None
        id_content = 200

        data = generate_code(self.student, str(self.course.id), 3093, id_content)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 6)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch("corfogeneratecode.views.get_grade_cutoff")
    @patch('requests.post')
    def test_generate_code_request_grade_cutoff_none(self, post, grade_cutoff):
        """
            test views.generate_code(request) when get_grade_cutoff failed
        """
        
        EdxLoginUser.objects.create(user=self.student, run='009472337K')

        
        grade_cutoff.return_value = None
        id_content = 200
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 7)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_success(self, post):
        """
            test views.generate_code(request) success process
        """
        CorfoCodeInstitution.objects.create(id_institution=3094)
        
        EdxLoginUser.objects.create(user=self.student, run='009472337K')


        id_content = 200
        post_data = {
                'Data': 0,
                'Message': None,
                'Status': 0,
                'Success': True
            }
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data) ,namedtuple("Request", ["status_code", "json"])(200, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'success')
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content__id_content=id_content)
            self.assertEqual(data['code'], corfouser.code)
            self.assertTrue(corfouser.corfo_save)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_success_with_passport(self, post):
        """
            test views.generate_code(request) success process
        """
        CorfoCodeInstitution.objects.create(id_institution=3094)
        
        EdxLoginUser.objects.create(user=self.student, run='P09472337K')


        id_content = 200
        post_data = {
                'Data': 0,
                'Message': None,
                'Status': 0,
                'Success': True
            }
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data) ,namedtuple("Request", ["status_code", "json"])(200, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'success')
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content__id_content=id_content)
            self.assertEqual(data['code'], corfouser.code)
            self.assertTrue(corfouser.corfo_save)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_generate_code_request_validate_no_id_institution(self, post):
        """
            test views.generate_code(request) when post validate without id_institution
        """
        
        EdxLoginUser.objects.create(user=self.student, run='009472337K')


        id_content = 200
        post_data = {"Message":"An error has occurred."}
        resp_data = {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ"
        }
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data), namedtuple("Request", ["status_code", "json"])(200, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            data = generate_code(self.student, str(self.course.id), 3093, id_content)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 3)
            mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
            corfouser = CorfoCodeUser.objects.get(user=self.student, mapping_content=mapp_content)
            self.assertFalse(corfouser.corfo_save)
            self.assertTrue(corfouser.code != '')

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @patch('requests.post')
    def test_get_token_post_connection_error(self, post):
        """
            test views.get_token when post return exception connection error
        """
        post.side_effect = Exception("Connection error")
        with self.assertLogs('corfogeneratecode.views', level='ERROR') as cm:
            result = get_token()
        self.assertEqual(result, {'result': 'error'})
        self.assertIn('CorfoGenerateCode - Error to get token, exception:', cm.output[0])
        
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_validate_mooc_error_has_ocurred(self, post):
        """
            test views.validate_mooc when post return exception An error has occurred.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Message":"An error has occurred."}
        mock_response.text = str(mock_response.json.return_value)

        post.return_value = mock_response
        with self.assertLogs('corfogeneratecode.views', level='ERROR') as cm:
            result = validate_mooc(
                token='fake-token',
                code='ABC123',
                score=90,
                id_content=1,
                user_rut='12345678-9',
                email='test@example.com',
                id_institution='999'
            )
        self.assertIn('CorfoGenerateCode - Error to validate api, user_rut: 12345678-9', cm.output[0])
        self.assertEqual(result['result'], 'error')
