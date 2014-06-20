# coding=utf8

import socket
from mustaine.client import HessianProxy

def test_proxy_client_when_using_localhost_as_proxy():
    test = HessianProxy("http://hessian.caucho.com/test/test", proxy_uri="http://localhost:8080")
    raised_connect_error = False
    try:
        test.argDouble_0_0(0.0)
    except socket.error:
        raised_connect_error = True
    assert raised_connect_error == True

def test_proxy_client_when_using_request_url_as_proxy():
    test = HessianProxy("http://hessian.caucho.com/test/test", proxy_uri="http://hessian.caucho.com/test/test")
    raised_connect_error = False
    try:
        test.argDouble_0_0(0.0)
    except socket.error:
        raised_connect_error = True
    assert raised_connect_error == False

def test_proxy_client_when_not_using_proxy():
    test = HessianProxy("http://hessian.caucho.com/test/test")
    raised_connect_error = False
    try:
        test.argDouble_0_0(0.0)
    except socket.error:
        raised_connect_error = True
    assert raised_connect_error == False
