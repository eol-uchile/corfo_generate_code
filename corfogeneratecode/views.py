#!/usr/bin/env python
# -- coding: utf-8 --

from django.conf import settings
from django.shortcuts import render
from django.views.generic.base import View
from django.contrib.auth.base_user import BaseUserManager
from lms.djangoapps.courseware.courses import get_course_by_id
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from django.http import Http404, HttpResponse, JsonResponse
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from .models import CorfoCodeUser
from django.core.cache import cache
import requests
import json
import logging

logger = logging.getLogger(__name__)

def generate_code(request):
    if request.method != "GET":
        return HttpResponse(status=400)

    if validate_data(request):
        course_key = CourseKey.from_string(request.GET.get('course_id'))
        passed, percent = user_course_passed(request.user, course_key)
        if passed is None:
            return JsonResponse({'result':'error', 'status': 6, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda.'}, safe=False)
        if passed is False:
            logger.error('CorfoGenerateCode - User dont passed course, user: {}, course: {}'.format(request.user, str(course_key)))
            return JsonResponse({'result':'error', 'status': 0, 'message': 'Usuario no ha aprobado el curso todavía.'}, safe=False)
        corfouser, created = CorfoCodeUser.objects.get_or_create(user=request.user, course=course_key)
        if corfouser.code != '':
            logger.info('CorfoGenerateCode - User already have code, user: {}, course: {}'.format(request.user, str(course_key)))
            return JsonResponse({'result':'success', 'code': corfouser.code}, safe=False)
        token = get_credentential()
        if token is None:
            logger.error('CorfoGenerateCode - Error to get token, user: {}, course: {}'.format(request.user, str(course_key)))
            return JsonResponse({'result':'error', 'status': 1, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda.'}, safe=False)
        
        user_rut = get_user_rut(corfouser)
        if user_rut is None:
            logger.error('CorfoGenerateCode - User dont have edxloginuser.run, user: {}, course: {}'.format(request.user, str(course_key)))
            return JsonResponse({'result':'error', 'status': 2, 'message': 'Usuario no tiene su Rut configurado, contáctese con mesa de ayuda (eol-ayuda@uchile.cl) para más información'}, safe=False)

        id_content = request.GET.get('id_content')
        content = request.GET.get('content')
        code = generate_code_corfo(request.user.id)
        grade_cutoff = get_grade_cutoff(course_key)
        if grade_cutoff is None:
            return JsonResponse({'result':'error', 'status': 7, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda.'}, safe=False)
        score = grade_percent_scaled(percent, grade_cutoff)
        response = validate_mooc(token, code, str(score), id_content, content, user_rut)
        if response['result'] == 'error':
            logger.error('CorfoGenerateCode - Error to validate api, user: {}, course: {}, response: {}'.format(request.user, str(course_key), response))
            return JsonResponse({'result':'error', 'status': 3, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda.'}, safe=False)
        if response['Status'] != 0 or response['Data'] is None:
            logger.error('CorfoGenerateCode - Error validate api in status or data, response: {}'.format(request.user, str(course_key), response))
            return JsonResponse({'result':'error', 'status': 4, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda.'}, safe=False)
        
        corfouser.code = code
        corfouser.save()
        return JsonResponse({'result':'success', 'code': code}, safe=False)
    return JsonResponse({'result':'error', 'status': 5, 'message': 'Usuario no ha iniciado sesión o error en parámetros, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda.'}, safe=False)

def get_user_rut(corfouser):
    """
        Get user.rut from EdxLoginUser model
    """
    try:
        aux_run = corfouser.user.edxloginuser.run
        run = str(int(aux_run[:-1])) + aux_run[-1]
        return run
    except AttributeError:
        return None

def validate_data(request):
    """
        Validate data
    """
    if request.user.is_anonymous:
        logger.error('CorfoGenerateCode - User is anonymous')
        return False
    if request.GET.get('id_content','') == '' :
        logger.error('CorfoGenerateCode - id_content is empty, user: {}, course: {}'.format(request.user, request.GET.get('course_id','')))
        return False
    if request.GET.get('content', '') == '':
        logger.error('CorfoGenerateCode - content is empty, user: {}, course: {}'.format(request.user, request.GET.get('course_id','')))
        return False
    try:
        course_key = CourseKey.from_string(request.GET.get('course_id',''))
    except InvalidKeyError:
        logger.error('CorfoGenerateCode - InvalidKeyError course_id, user: {}, course: {}'.format(request.user, request.GET.get('course_id','')))
        return False

    return True

def user_course_passed(user, course_key):
    """
       Get if user passed course with percert
    """
    response = CourseGradeFactory().read(user, course_key=course_key)
    if response is None:
        logger.error('CorfoGenerateCode - Error to get CourseGradeFactory().read(...), user: {}, course: {}'.format(user, str(course_key)))
        return None, None
    return response.passed, response.percent

def get_token():
    """
       Get corfo token
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset:UTF-8"
    }
    body = {
        "scope": 'resource.READ',
        "client_secret": settings.CORFOGENERATE_CLIENT_SECRET,
        "client_id": settings.CORFOGENERATE_CLIENT_ID,
        "grant_type": 'client_credentials'
    }
    r = requests.get(
        settings.CORFOGENERATE_URL_TOKEN,
        data=json.dumps(body),
        headers=headers)
    if r.status_code == 200:
        data = r.json()
        print(data)
        data['result'] = 'success'
        return data
    else:
        return {'result':'error'}

def get_credentential():
    """
       Get corfo token and save it in cache if fail return None
    """
    token = cache.get("corfogeneratecode-token")
    if token is None:
        data = get_token()
        """
        {
            "access_token": "IE742SAsEMadiliCt1w582TMnvj98aDyS6L7BXSFP84vto914p77nX",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "resource.READ",
            "result": 'success'
        }
        """
        if data['result'] == 'error':
            token = None
        else:
            token = data['access_token']
            cache.set("corfogeneratecode-token", token, 60*30)
    
    return token

def validate_mooc(token, code, score, id_content, content, user_rut):
    """
       Post to Corfo with user data
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        'Authorization': 'Bearer  {}'.format(token)
    }
    body = {
        "Institucion": settings.CORFOGENERATE_ID_INSTITUTION,
        "Rut": user_rut,
        "Contenido": id_content,
        "NombreContenido": content,
        "CodigoCertificacion": code,
        "Evaluacion": score
    }
    r = requests.post(
        settings.CORFOGENERATE_URL_VALIDATE,
        data=json.dumps(body),
        headers=headers)
    if r.status_code == 200:
        data = r.json()
        data['result'] = 'success'
        return data
    else:
        return {'result':'error'}

def generate_code_corfo(user_id):
    """
       Generate Corfo Code
    """
    aux_code = BaseUserManager().make_random_password(8).upper()
    code = 'U{}COD{}'.format(user_id, aux_code)
    return code

def get_grade_cutoff(course_key):
    """
       Get course grade_cutoffs
    """
    # Load the course and user objects
    try:
        course = get_course_by_id(course_key)
        grade_cutoff = min(course.grade_cutoffs.values())  # Get the min value
        return grade_cutoff
    # For any course or user exceptions, kick the user back to the "Invalid" screen
    except (InvalidKeyError, Http404) as exception:
        error_str = (
            u"Invalid cert: error finding course %s "
            u"Specific error: %s"
        )
        log.error(error_str, str(course_key), str(exception))
        return None

def grade_percent_scaled( grade_percent, grade_cutoff):
    """
        EOL: Scale grade percent by grade cutoff. Grade between 1.0 - 7.0
    """
    if grade_percent == 0.:
        return 1.
    if grade_percent < grade_cutoff:
        return round(10. * (3. / grade_cutoff * grade_percent + 1.)) / 10.
    return round((3. / (1. - grade_cutoff) * grade_percent + (7. - (3. / (1. - grade_cutoff)))) * 10.) / 10.