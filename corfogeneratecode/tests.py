#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mock import patch, Mock
from collections import namedtuple
from django.test import Client
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
import json
from xblock.field_data import DictFieldData
from .views import user_course_passed, grade_percent_scaled, generate_code
from .corfogeneratecode import CorfoGenerateXBlock
from .models import CorfoCodeUser, CorfoCodeMappingContent, CorfoCodeInstitution
from lms.djangoapps.grades.tests.utils import mock_get_score
from lms.djangoapps.grades.tests.base import GradeTestBase
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from django.test.utils import override_settings

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
            self.assertEqual(response['user_rut'], '')
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
            self.assertEqual(response['user_rut'], '')
            self.assertEqual(response['corfo_save'], True)


    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @patch('requests.post')
    def test_block_generate_code(self, post):
        """
            Verify generate_code() is working
        """
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
    def test_block_generate_code_with_passport(self, post):
        """
            Verify generate_code() is working whern user have passport
        """
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='P009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='CA009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
            Verify method user_course_passed() work correctly
        """
        with mock_get_score(1, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(1, 4):
            passed, percent = user_course_passed(self.student, self.course.id)            
            self.assertEqual(percent, 0.25)
            self.assertFalse(passed)

    def test_round_half_up(self):
        """
            Verify method grade_percent_scaled() work correctly
        """
        grades = [1,1.1,1.1,1.2,1.2,1.3,1.3,1.4,1.4,1.5,1.5,1.6,1.6,1.7,1.7,1.8,1.8,1.9,1.9,2,2,2.1,2.1,2.2,2.2,2.3,2.3,2.4,2.4,2.5,2.5,2.6,2.6,2.7,2.7,2.8,2.8,2.9,2.9,3,3,3.1,3.1,3.2,3.2,3.3,3.3,3.4,3.4,3.5,3.5,3.6,3.6,3.7,3.7,3.8,3.8,3.9,3.9,4,4,4.1,4.2,4.2,4.3,4.4,4.5,4.5,4.6,4.7,4.8,4.8,4.9,5,5.1,5.1,5.2,5.3,5.4,5.4,5.5,5.6,5.7,5.7,5.8,5.9,6,6,6.1,6.2,6.3,6.3,6.4,6.5,6.6,6.6,6.7,6.8,6.9,6.9,7]
        for i in range(101):
            self.assertEqual(grade_percent_scaled(i/100,0.6), grades[i])

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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='CA09472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")
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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='0947P2337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")
        
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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")
        
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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='P09472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

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
