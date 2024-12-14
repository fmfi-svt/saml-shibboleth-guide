from html import escape
from pathlib import Path

def status_page(titleword, environ, start_response):
    pieces = []
    def write(p):
        pieces.append(p + '\n')
    def menu(prefix, links):
        write('<p>' + prefix + ' | '.join(
            f'<a href="{escape(h)}">{escape(t)}</a>' for h, t in links))

    host = environ['HTTP_HOST']
    hostfirst, _, hostrest = host.partition('.')
    title = f'{hostfirst} {titleword}, logged ' + ('IN' if environ.get('AUTH_TYPE') else 'out')

    write('<!DOCTYPE html>')
    write('<meta charset="UTF-8">')
    write(f'<title>{escape(title)}</title>')
    write('<div style="font-size: 2em">')
    write(f'<h1 style="margin: auto">{escape(title)}</h1>')
    menu('here: ', [('/', 'public page'), ('/secret/', 'secret page')])
    if 'mellon' in host:
        menu('mellon: ', [
            ('/mellon/login?ReturnTo=/', 'login'),
            ('/mellon/logout?ReturnTo=/', 'logout'),
            ('/mellon/invalidate?ReturnTo=/', 'invalidate'),
        ])
    if 'shib' in host:
        menu('shib: ', [
            ('/Shibboleth.sso/Login?target=/', 'login'),
            ('/Shibboleth.sso/Logout?return=/', 'logout'),
            ('/Shibboleth.sso/Status', 'status'),
            ('/Shibboleth.sso/Session', 'session'),
        ])
    sites = []
    for child in sorted(Path('/etc/apache2/sites-enabled').iterdir()):
        name = child.name.partition('.')[0]
        if 'default' in name: continue
        sites.append((f'https://{name}.{hostrest}/', name))
        if name == 'idp':
            sites.append((f'https://idp.{hostrest}/idp/', 'idp/idp'))
            sites.append((f'https://idp.{hostrest}/idp/profile/admin/hello', 'idp/...hello'))
    menu('sites: ', sites)

    write('</div>')
    write('<h2>WSGI environment</h2>')
    write('<pre style="white-space: pre-wrap; word-break: break-all">{')
    for k, v in sorted(environ.items()):
        write(escape(f'  {k!r}: {v!r},'))
    write('}</pre>')

    start_response('200 OK', [('Content-Type', 'text/html;charset=UTF-8')])
    return [''.join(pieces).encode('utf-8')]

def application(environ, start_response):
    if environ['PATH_INFO'] == '/':
        return status_page('public', environ, start_response)
    if environ['PATH_INFO'] == '/secret/':
        return status_page('SECRET', environ, start_response)
    start_response('404 Not Found', [('Content-Type', 'text/html;charset=UTF-8')])
    return [b'404 Not Found']
