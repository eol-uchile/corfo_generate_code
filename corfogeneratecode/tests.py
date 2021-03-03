#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mock import patch, Mock, MagicMock
from collections import namedtuple
from django.urls import reverse
from django.test import TestCase, Client
from django.test import Client
from django.conf import settings
from django.contrib.auth.models import User
from util.testing import UrlResetMixin
from urllib.parse import parse_qs
from opaque_keys.edx.locator import CourseLocator
from student.tests.factories import CourseEnrollmentAllowedFactory, UserFactory, CourseEnrollmentFactory
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.roles import CourseInstructorRole, CourseStaffRole
import json
import urllib.parse
from xblock.field_data import DictFieldData
from .views import user_course_passed
from .corfogeneratecode import CorfoGenerateXBlock
from .models import CorfoCodeUser, CorfoCodeMappingContent
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
        with patch('student.models.cc.User.save'):
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
    
    def test_edit_block_studio_string_id(self):
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

    def test_student_view(self):
        """
            Verify context in student_view
        """
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context()
        self.assertEqual(response['passed'], False)
        self.assertEqual(response['code'], '')

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

    def test_student_view_user_passed_course_with_code(self):
        """
            Verify context in student_view when user has passed the course and have code
        """
        corfouser = CorfoCodeUser.objects.create(user=self.student, course=self.course.id, code='U1CODASDFGH')
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            self.xblock.scope_ids.user_id = self.student.id
            response = self.xblock.get_context()
            self.assertEqual(response['passed'], True)
            self.assertEqual(response['code'], corfouser.code)

class TestCorfoGenerateView(GradeTestBase):

    def setUp(self):
        super(TestCorfoGenerateView, self).setUp()        

        self.grade_factory = CourseGradeFactory()
        CorfoCodeMappingContent.objects.create(id_content=200, content='testtest')
        with patch('student.models.cc.User.save'):
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
    
    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    def test_generate_code_request(self):
        """
            test views.generate_code(request) without user data
        """
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }

        response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
        data = json.loads(response._container[0].decode())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 0)

    def test_generate_code_request_post_method(self):
        """
            test views.generate_code(request) wrong method
        """
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }

        response = self.student_client.post(reverse('corfogeneratecode:generate'), get_data)
        self.assertEqual(response.status_code, 400)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    def test_generate_code_request_user_with_code(self):
        """
            test views.generate_code(request) when user already have code
        """
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
        corfouser = CorfoCodeUser.objects.create(user=self.student, course=self.course.id, code='U1CODASDFGH')
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'success')
            self.assertEqual(data['code'], corfouser.code)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    @patch('requests.post')
    def test_generate_code_request_fail_token(self, post):
        """
            test views.generate_code(request) when get toket failed
        """
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
        post.side_effect = [namedtuple("Request", ["status_code"])(400)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 1)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    @patch('requests.post')
    def test_generate_code_request_user_no_rut(self, post):
        """
            test views.generate_code(request) when user dont have edxloginuser.rut
        """
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
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
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 2)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
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
        
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
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
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data), namedtuple("Request", ["status_code", "json"])(400, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 3)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
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

        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
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
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:resp_data), namedtuple("Request", ["status_code", "json"])(200, lambda:post_data)]
        with mock_get_score(3, 4):
            self.grade_factory.update(self.student, self.course, force_update_subsections=True)
        with mock_get_score(3, 4):
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 4)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    def test_generate_code_request_wrong_course(self):
        """
            test views.generate_code(request) wrong method
        """
        get_data = {
                'course_id': 'ads',
                'id_content': '200',
                'content': 'testtest'
            }

        response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
        data = json.loads(response._container[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    def test_generate_code_request_no_id_content(self):
        """
            test views.generate_code(request) without id_content
        """
        get_data = {
                'course_id': 'ads',
                'id_content': '',
                'content': 'testtest'
            }

        response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
        data = json.loads(response._container[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    def test_generate_code_request_no_content(self):
        """
            test views.generate_code(request) without content
        """
        get_data = {
                'course_id': 'ads',
                'id_content': '200',
                'content': ''
            }

        response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
        data = json.loads(response._container[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    def test_generate_code_request_no_mapping(self):
        """
            test views.generate_code(request) when CorfoCodeMappingContent.DoesNotExist
        """
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '404',
                'content': 'a'
            }

        response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
        data = json.loads(response._container[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)
    
    @override_settings(CORFOGENERATE_URL_TOKEN="")
    @override_settings(CORFOGENERATE_CLIENT_ID="")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="")
    @override_settings(CORFOGENERATE_URL_VALIDATE="")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=0)
    def test_generate_code_request_no_settings(self):
        """
            test views.generate_code(request) when settings no configurate
        """
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '404',
                'content': 'a'
            }

        response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
        data = json.loads(response._container[0].decode())
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 5)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    @patch("corfogeneratecode.views.user_course_passed")
    def test_generate_code_request_passed_none(self, passed):
        """
            test views.generate_code(request) when get user_course_passed failed
        """
        passed.return_value = None, None
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }

        response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
        data = json.loads(response._container[0].decode())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['result'], 'error')
        self.assertEqual(data['status'], 6)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
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
        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
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
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 7)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
    @patch('requests.post')
    def test_generate_code_success(self, post):
        """
            test views.generate_code(request) success process
        """
        try:
            from unittest.case import SkipTest
            from uchileedxlogin.models import EdxLoginUser
            EdxLoginUser.objects.create(user=self.student, run='009472337K')
        except ImportError:
            self.skipTest("import error uchileedxlogin")

        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
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
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'success')
            corfouser =  CorfoCodeUser.objects.get(user=self.student, course=self.course.id)
            self.assertEqual(data['code'], corfouser.code)

    @override_settings(CORFOGENERATE_URL_TOKEN="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_ID="aaaaa")
    @override_settings(CORFOGENERATE_CLIENT_SECRET="aaaaa")
    @override_settings(CORFOGENERATE_URL_VALIDATE="aaaaa")
    @override_settings(CORFOGENERATE_ID_INSTITUTION=111)
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

        get_data = {
                'course_id': str(self.course.id),
                'id_content': '200',
                'content': 'testtest'
            }
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
            response = self.student_client.get(reverse('corfogeneratecode:generate'), get_data)
            data = json.loads(response._container[0].decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['result'], 'error')
            self.assertEqual(data['status'], 3)