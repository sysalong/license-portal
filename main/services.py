from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep.transports import Transport
from zeep import Client as ZeepClient
# from zeep.cache import SqliteCache
from zeep.wsse.username import UsernameToken

from license_portal.settings import DEBUG, EFILE_WEBSERVICE_URL, MERAS_CLIENT_ID, MERAS_CLIENT_SECRET, WATHIQ_URL, WATHIQ_USERNAME, WATHIQ_PASSWORD


def make_efile_client():
    if DEBUG:
        session = Session()
        session.verify = False

        client = ZeepClient(EFILE_WEBSERVICE_URL, transport=Transport(session=session))
    else:
        # TODO: CHECK WHEN ON PRODUCTION IF AUTH HEADER IS NEEDED AND IF SESSION.VERIFY SHOULD BE FALSE TOO
        client = ZeepClient(EFILE_WEBSERVICE_URL)

    return client


def make_wathiq_client():
    if DEBUG:
        session = Session()
        session.verify = False

        token = UsernameToken(WATHIQ_USERNAME, WATHIQ_PASSWORD)

        try:
            client = ZeepClient(WATHIQ_URL, transport=Transport(session=session), wsse=token)
        except Exception as e:
            print('EXCEPTION:make_wathiq_client -> ', e)
            client = None

    else:
        # TODO: CHECK ON PRODUCTION IF SESSION.VERIFY SHOULD BE FALSE TOO
        client = ZeepClient(WATHIQ_URL, wsse=UsernameToken(WATHIQ_USERNAME, WATHIQ_PASSWORD))

    return client


class EFileService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = make_efile_client()
        return cls._instance

    @classmethod
    def is_authenticated(cls, access_token):
        client = cls.get_instance()

        try:
            return client.service.IsAuthenticated(access_token, MERAS_CLIENT_ID)
        except:
            return False

    @classmethod
    def get_username_by_access_token(cls, access_token):
        client = cls.get_instance()

        try:
            return client.service.GetUsernameByAccessToken(access_token)
        except:
            return '<NIL>'

    @classmethod
    def logout(cls, access_token):
        client = cls.get_instance()

        try:
            return client.service.Logout(access_token)
        except Exception as e:
            return e

    @classmethod
    def get_person_by_nid(cls, national_id):
        client = cls.get_instance()

        try:
            return client.service.GetPersonByNID(national_id, MERAS_CLIENT_ID, MERAS_CLIENT_SECRET)
        except:
            return False

    @classmethod
    def authenticated(cls, national_id):
        client = cls.get_instance()

        try:
            return client.service.Authenticated(MERAS_CLIENT_ID, MERAS_CLIENT_SECRET, national_id)
        except Exception as e:
            return e


class WathiqService:
    _instance = None
    _iattempts = 0

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            while cls._iattempts < 10:
                cls._instance = make_wathiq_client()
                cls._iattempts += 1
        return cls._instance

    @classmethod
    def has_cr_by_id(cls, nid):
        client = cls.get_instance()

        try:
            return client.service.HasCRByID(nid)
        except Exception as e:
            print('EXCEPTION:has_cr_by_id -> ', e)
            return False

    @classmethod
    def get_crs_by_id(cls, nid):
        client = cls.get_instance()

        try:
            res = client.service.GetCRsByID(nid)
            if res:
                return [cr.__dict__['__values__'] for cr in res]
            return []
        except Exception as e:
            print('EXCEPTION:get_crs_by_id -> ', e)
            return []
