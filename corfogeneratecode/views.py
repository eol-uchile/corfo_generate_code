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
from .models import CorfoCodeUser, CorfoCodeMappingContent, CorfoCodeInstitution
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.core.cache import cache
import requests
import json
import logging

logger = logging.getLogger(__name__)

def generate_code(user, course_id, id_institution, id_content):
    if validate_data(user, course_id, id_institution, id_content):
        course_key = CourseKey.from_string(course_id)
        passed, percent = user_course_passed(user, course_key)
        id_content = int(id_content)
        id_institution = int(id_institution)
        if passed is None:
            return {'result':'error', 'status': 6, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}
        if passed is False:
            logger.error('CorfoGenerateCode - User dont passed course, user: {}, course: {}'.format(user, course_id))
            return {'result':'error', 'status': 0, 'message': 'Usuario no ha aprobado el curso todavía.'}
        mapp_content = CorfoCodeMappingContent.objects.get(id_content=id_content)
        corfouser, created = CorfoCodeUser.objects.get_or_create(user=user, mapping_content=mapp_content)
        user_rut = get_user_rut(corfouser)
        if corfouser.corfo_save and corfouser.code != '':
            logger.info('CorfoGenerateCode - User already have code, user: {}, course: {}'.format(user, course_id))
            return {'result':'success', 'code': corfouser.code, 'user_rut': user_rut}

        if corfouser.code == '':
            corfouser.code = generate_code_corfo(user.id)
            corfouser.corfo_save = False
            corfouser.created_at = datetime.now()
            corfouser.save()
        token = get_credentential()
        if token is None:
            logger.error('CorfoGenerateCode - Error to get token, user: {}, course: {}'.format(user, course_id))
            return {'result':'error', 'status': 1, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}

        if user_rut is None:
            logger.error('CorfoGenerateCode - User dont have edxloginuser.run, user: {}, course: {}'.format(user, course_id))
            return {'result':'error', 'status': 2, 'message': 'Usuario no tiene su Rut configurado, contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a> para más información'}

        grade_cutoff = get_grade_cutoff(course_key)
        if grade_cutoff is None:
            return {'result':'error', 'status': 7, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a><a href="/contact_form" target="_blank">presionando aquí</a>.'}

        score = grade_percent_scaled(percent, grade_cutoff)
        response = validate_mooc(token, corfouser.code, str(score), id_content, user_rut, user.email, id_institution)
        if response['result'] == 'error':
            return {'result':'error', 'status': 3, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}
        if response['result'] == 'error_success':
            logger.error('CorfoGenerateCode - Error validate api in status or data, user: {}, course: {}, response: {}'.format(user, course_id, response))
            return {'result':'error', 'status': 4, 'message': 'Un error inesperado ha ocurrido, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}

        corfouser.corfo_save = True
        corfouser.created_at = datetime.now()
        corfouser.save()
        return {'result':'success', 'code': corfouser.code, 'user_rut': user_rut}
    return {'result':'error', 'status': 5, 'message': 'Usuario no ha iniciado sesión o error en parámetros, actualice la página e intente nuevamente, si el problema persiste contáctese con mesa de ayuda <a href="/contact_form" target="_blank">presionando aquí</a>.'}

def get_user_rut(corfouser):
    """
        Get user.rut from EdxLoginUser model
    """
    try:
        aux_run = corfouser.user.edxloginuser.run
        if aux_run[0] == 'P':
            return aux_run
        elif aux_run[0].isalpha():
            return None
        else:
            run = str(int(aux_run[:-1])) + aux_run[-1]
            return run
    except (AttributeError, ValueError) as e:
        return None

def validate_data(user, course_id, id_institution, id_content):
    """
        Validate data
    """
    if check_settings():
        logger.error('CorfoGenerateCode - settings no configurate')
        return False

    if user.is_anonymous:
        logger.error('CorfoGenerateCode - User is anonymous')
        return False
    try:
        if int(id_content) == 0:
            logger.error('CorfoGenerateCode - id_content is empty, user: {}, course: {}'.format(user, course_id))
            return False
    except ValueError:
        logger.error('CorfoGenerateCode - id_content is not Integer, user: {}, course: {}, id_content: {}'.format(user, course_id, id_content))
        return False

    try:
        if int(id_institution) != 3093:
            institution = CorfoCodeInstitution.objects.get(id_institution=int(id_institution))
    except (ValueError, CorfoCodeInstitution.DoesNotExist ) as e:
        logger.error('CorfoGenerateCode - id_institution is not Integer or dont exists, user: {}, course: {}, id_institution: {}'.format(user, course_id, id_institution))
        return False

    try:
        course_key = CourseKey.from_string(course_id)
    except InvalidKeyError:
        logger.error('CorfoGenerateCode - InvalidKeyError course_id, user: {}, course: {}'.format(user, course_id))
        return False
    try:
        corfomapping = CorfoCodeMappingContent.objects.get(id_content=int(id_content))
    except CorfoCodeMappingContent.DoesNotExist:
        logger.error('CorfoGenerateCode - CorfoCodeMappingContent.DoesNotExist user: {}, course: {}, id_content: {}'.format(user, course_id, id_content))
        return False
    return True

def check_settings():
    return (is_empty(settings.CORFOGENERATE_URL_TOKEN) or
        is_empty(settings.CORFOGENERATE_CLIENT_ID) or
        is_empty(settings.CORFOGENERATE_CLIENT_SECRET) or
        is_empty(settings.CORFOGENERATE_URL_VALIDATE))

def is_empty(attr):
    """
        check if attribute is empty or None
    """
    return attr == "" or attr == 0 or attr is None

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
    try:
        r = requests.post(
            settings.CORFOGENERATE_URL_TOKEN,
            data=body,
            headers=headers, verify=False)
        if r.status_code == 200:
            data = r.json()
            data['result'] = 'success'
            return data
        else:
            return {'result':'error'}
    except Exception as e:
        logger.error('CorfoGenerateCode - Error to get token, exception: {}'.format(str(e)))
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
            "access_token":"asdadasdsa",
            "token_type":"Bearer",
            "expires_in":3600,
            "scope":"resource.READ",
            "appName":"Universidad de Chile"
            "result": 'success'
        }
        """
        if data['result'] == 'error':
            token = None
        else:
            token = data['access_token']
            cache.set("corfogeneratecode-token", token, 60*30)
    
    return token

def validate_mooc(token, code, score, id_content, user_rut, email, id_institution):
    """
       Post to Corfo with user data
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        'Authorization': 'Bearer {}'.format(token)
    }
    body = {
        "Institucion": id_institution,
        "Rut": user_rut,
        "Contenido": id_content,
        "NombreContenido": '',
        "CodigoCertificacion": code,
        "Evaluacion": float(score),
        "Correo": email
    }
    message_error = {"Message":"An error has occurred."}
    try:
        r = requests.post(
            settings.CORFOGENERATE_URL_VALIDATE,
            data=body,
            headers=headers, verify=False)
        if r.status_code == 200:
            data = r.json()
            if data == message_error:
                logger.error('CorfoGenerateCode - Error to validate api, user_rut: {}, response: {}, response_status_code: {}'.format(user_rut, r.text, r.status_code))
                return {'result':'error'}
            elif not data['Success']:
                logger.error('CorfoGenerateCode - Error to validate api, user_rut: {}, response: {}, response_status_code: {}'.format(user_rut, r.text, r.status_code))
                data['result'] = 'error_success'
            else:
                data['result'] = 'success'
            return data
        else:
            logger.error('CorfoGenerateCode - Error to validate api, user_rut: {}, response: {}, response_status_code: {}'.format(user_rut, r.text, r.status_code))
            return {'result':'error'}
    except Exception as e:
        logger.error('CorfoGenerateCode - Error to validate_mooc, exception: {}'.format(str(e)))
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
        logger.error(error_str, str(course_key), str(exception))
        return None

def grade_percent_scaled(grade_percent, grade_cutoff):
    """
        EOL: Scale grade percent by grade cutoff. Grade between 1.0 - 7.0
    """
    if grade_percent == 0.:
        return 1.
    if grade_percent < grade_cutoff:
        return round_up((Decimal('3') / Decimal(str(grade_cutoff)) * Decimal(str(grade_percent)) + Decimal('1')))
    return round_up(Decimal('3') / Decimal(str(1. - grade_cutoff)) * Decimal(str(grade_percent)) + (Decimal('7') - (Decimal('3') / Decimal(str(1. - grade_cutoff)))))

def round_up(number):
    return float(Decimal(str(float(number))).quantize(Decimal('0.1'), ROUND_HALF_UP))