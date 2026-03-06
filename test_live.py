import urllib.request as r
import urllib.parse as p
import http.cookiejar
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

cj = http.cookiejar.CookieJar()
opener = r.build_opener(r.HTTPCookieProcessor(cj), r.HTTPSHandler(context=ctx))
r.install_opener(opener)

try:
    print("Sending GET /login")
    req = r.Request('https://gestaodecomissao.onrender.com/login')
    res = r.urlopen(req)
    print("GET Login code:", res.getcode())
except Exception as e:
    print("GET Login Exception:", e)

try:
    print("Sending POST /register")
    data = p.urlencode({'full_name': 'test_render', 'password': 'abc'}).encode('utf-8')
    req = r.Request('https://gestaodecomissao.onrender.com/register', data=data)
    res = r.urlopen(req)
    print("POST Register code:", res.getcode())
except Exception as e:
    print("POST Register Exception:", e)
    if hasattr(e, 'read'):
        body = e.read().decode('utf-8')
        print("Body preview:", body)
        if '<pre>' not in body:
            print("Render has NOT deployed the new code yet (or the generic error is from Gunicorn).")
        else:
            print("Traceback found!")

