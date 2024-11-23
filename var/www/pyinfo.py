def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain;charset=UTF-8')])
    items = ''.join(f'  {k!r}: {v!r},\n' for k, v in sorted(environ.items()))
    body = '{\n' + items + '}'
    return [body.encode('utf-8')]
