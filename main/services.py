# from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep.transports import Transport
from zeep import Client as ZeepClient

from license_portal.settings import DEBUG, EFILE_WEBSERVICE_URL, MERAS_CLIENT_ID, MERAS_CLIENT_SECRET


def make_client():
    if DEBUG:
        session = Session()
        session.verify = False

        client = ZeepClient(EFILE_WEBSERVICE_URL, transport=Transport(session=session))
    else:
        client = ZeepClient(EFILE_WEBSERVICE_URL)

    return client


class EFileService:
    @staticmethod
    def is_authenticated(access_token):
        # user = 'WathiqSTATSPP'
        # password = 'bFGT776&UYTRE123'
        session = Session()
        session.verify = False
        # session.auth = HTTPBasicAuth(user, password)
        # client = Client('http://my-endpoint.com/production.svc?wsdl', transport=Transport(session=session))

        client = make_client()

        try:
            return client.service.IsAuthenticated(access_token, MERAS_CLIENT_ID)
        except:
            return False

    @staticmethod
    def get_username_by_access_token(access_token):
        client = make_client()

        try:
            return client.service.GetUsernameByAccessToken(access_token)
        except:
            return '<NIL>'

    @staticmethod
    def logout(access_token):
        client = make_client()

        try:
            return client.service.Logout(access_token)
        except Exception as e:
            return e

    @staticmethod
    def get_person_by_nid(national_id):
        client = make_client()

        try:
            return client.service.GetPersonByNID(national_id, MERAS_CLIENT_ID, MERAS_CLIENT_SECRET)
        except:
            return False

    @staticmethod
    def authenticated(national_id):
        client = make_client()

        try:
            return client.service.Authenticated(MERAS_CLIENT_ID, MERAS_CLIENT_SECRET, national_id)
        except Exception as e:
            return e
