# Corfo Generate Code XBlock

![Coverage Status](/coverage-badge.svg)

![https://github.com/eol-uchile/corfo_generate_code/actions](https://github.com/eol-uchile/corfo_generate_code/workflows/Python%20application/badge.svg)

# Install

    docker-compose exec cms pip install -e /openedx/requirements/corfo_generate_code
    docker-compose exec lms pip install -e /openedx/requirements/corfo_generate_code
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations corfogeneratecode
    docker-compose exec lms python manage.py lms --settings=prod.production migrate

# Configuration

Edit *production.py* in *lms and cms settings* and add your own keys, redirect url to get token and validate_mooc.
    
    CORFOGENERATE_URL_TOKEN = AUTH_TOKENS.get('CORFOGENERATE_URL_TOKEN', '')
    CORFOGENERATE_CLIENT_ID = AUTH_TOKENS.get('CORFOGENERATE_CLIENT_ID', '')
    CORFOGENERATE_CLIENT_SECRET = AUTH_TOKENS.get('CORFOGENERATE_CLIENT_SECRET', '')
    CORFOGENERATE_URL_VALIDATE = AUTH_TOKENS.get('CORFOGENERATE_URL_VALIDATE', '')

Add id_institutions in CorfoCodeInstitution model, default id_institution=3093, name=EOL

## TESTS
**Prepare tests:**

- Install **act** following the instructions in [https://nektosact.com/installation/index.html](https://nektosact.com/installation/index.html)

**Run tests:**
- In a terminal at the root of the project
    ```
    act -W .github/workflows/pythonapp.yml

## Notes

-If CORFOGENERATE_URL_TOKEN or CORFOGENERATE_URL_VALIDATE are test environment, add verify=False to requests

