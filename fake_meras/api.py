# from flask import Flask, Response, request
# from flask.json import JSONEncoder

from __future__ import unicode_literals

import sys
import logging
import re
import traceback

try:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer

from pysimplesoap import server
from pysimplesoap.simplexml import SimpleXMLElement, TYPE_MAP, Date, Decimal

# from .data_cr import data_crs
# from .data_cr_data import data_cr_data
# from .data_cr_managers import data_cr_managers
# from .data_cr_ownerships import data_cr_ownerships
# from .data_cr_related_crs import data_cr_related_crs
# from .data_has_cr_by_id import data_has_cr_by_id

log = logging.getLogger(__name__)

if __name__ == "__main__":

    dispatcher = server.SoapDispatcher(
        name="PySimpleSoapSample",
        location="http://localhost:8008/",
        action='http://localhost:8008/',  # SOAPAction
        namespace="http://example.com/pysimplesoapsamle/", prefix="ns0",
        documentation='Example soap service using PySimpleSoap',
        trace=True,
        ns=True)

    def adder(p, c, dt=None):
        """Add several values"""
        import datetime
        dt = dt + datetime.timedelta(365)
        return {'ab': p['a'] + p['b'], 'dd': c[0]['d'] + c[1]['d'], 'dt': dt}

    def dummy(in0):
        """Just return input"""
        return in0

    def echo(request):
        """Copy request->response (generic, any type)"""
        return request.value

    dispatcher.register_function(
        'Adder', adder,
        returns={'AddResult': {'ab': int, 'dd': str}},
        args={'p': {'a': int, 'b': int}, 'dt': Date, 'c': [{'d': Decimal}]}
    )

    dispatcher.register_function(
        'Dummy', dummy,
        returns={'out0': str},
        args={'in0': str}
    )

    dispatcher.register_function('Echo', echo)

    if '--local' in sys.argv:

        wsdl = dispatcher.wsdl()

        for method, doc in dispatcher.list_methods():
            request, response, doc = dispatcher.help(method)

    if '--serve' in sys.argv:
        log.info("Starting server...")
        print("Starting server...")
        httpd = HTTPServer(("", 8008), server.SOAPHandler)
        httpd.dispatcher = dispatcher
        httpd.serve_forever()

    if '--wsgi-serve' in sys.argv:
        log.info("Starting wsgi server...")
        from wsgiref.simple_server import make_server
        application = server.WSGISOAPHandler(dispatcher)
        wsgid = make_server('', 8008, application)
        wsgid.serve_forever()

    if '--consume' in sys.argv:
        from pysimplesoap.client import SoapClient
        client = SoapClient(
            location="http://localhost:8008/",
            action='http://localhost:8008/',  # SOAPAction
            namespace="http://example.com/sample.wsdl",
            soap_ns='soap',
            trace=True,
            ns=False
        )
        p = {'a': 1, 'b': 2}
        c = [{'d': '1.20'}, {'d': '2.01'}]
        response = client.Adder(p=p, dt='20100724', c=c)
        result = response.AddResult
        log.info(int(result.ab))
        log.info(str(result.dd))


# def search_cr(by, value):
#     return [cr for cr in data_crs if cr[by] == value]


client_id = "5A036A93-60A0-44B5-AF3B-B6D3419AB8E5"

# app = Flask(__name__)
# json_encoder = JSONEncoder()


# def json_response(data):
#     return Response(json_encoder.encode(data))

client_secret = "secret12345"


# @app.route('/GetCRsByID', methods=['POST'])
# def get_crs_by_id():
#     # id = request.get_json()['ID']
#     #
#     # res = {
#     #     'CrListInfo': search_cr('NID', id)
#     # }
#     print(request.data)
#     print(request.get_json())
#     print(request.form)
#     print(request.args)
#     return json_response('')
#
#
# @app.route('/GetCRDataByCR')
# def get_cr_data_by_cr():
#     crno = request.get_json()['CrNo']
#
#     res = {
#         'CrInformation': {
#             'CR': crno,
#             'Name': 'some CR name',
#             'CRLocationID': 'manager',
#             'CRLocation': 5,
#             'BusType': 'manager',
#             'BusTypeID': 23
#         }
#     }
#
#     return json_response(res)
