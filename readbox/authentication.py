import logging
from django.utils import timezone
from pytz import utc
from tastypie.authentication import Authentication
from provider.oauth2.models import AccessToken
from django_facebook.connect import connect_user


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message


class OAuth20Authentication(Authentication):
    def __init__(self, realm='API'):
        self.realm = realm

    def is_authenticated(self, request, **kwargs):
        logging.info("OAuth20Authentication")

        try:
            auth_params = request.META.get("HTTP_AUTHORIZATION", '')
            if auth_params:
                parts = auth_params.split()
                if len(parts) == 2:
                    if parts[0] == 'OAuth':
                        key = parts[1]
                        token = verify_access_token(key)
                        request.user = token.user
                        return True
            return False
        except Exception, e:
            return False


def verify_access_token(key):
    try:
        token = AccessToken.objects.get(token=key)
        if token.expires.replace(tzinfo=utc) < timezone.now():
            raise OAuthError('AccessToken has expired.')
    except AccessToken.DoesNotExist, e:
        raise OAuthError("AccessToken not found at all.")
    logging.info('Valid access')
    return token


logger = logging.getLogger(__name__)


class FacebookAuthentication(Authentication):
    def __init__(self):
        super(FacebookAuthentication, self).__init__()

    def is_authenticated(self, request, **kwargs):
        auth_params = request.META.get("HTTP_AUTHORIZATION", '')
        if auth_params:
            parts = auth_params.split()
            if len(parts) == 2:
                if parts[0] == 'Facebook':
                    access_token = parts[1]
                    try:
                        action, user = connect_user(request, access_token=access_token)
                        return True
                    except Exception, err:
                        logger.error('ERROR {0}: {1}'.format(self.__class__.__name__, str(err)))

        return False