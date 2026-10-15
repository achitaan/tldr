import gzip
import io
import socket
import tempfile
import time
import threading
from email.message import Message
from pathlib import Path
from unittest import TestCase as UnitTestCase
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from . import web_ingestion as web
from .jobs import claim, run_job
from .models import Course, Source, Job
from .retrieval import retrieve

PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
HTML = r'<html><title>Derivative lesson</title><nav>UNWANTED MENU</nav><main><h1>The derivative</h1><p>The derivative measures instantaneous rate of change for a function at a point, using the limit of difference quotients.</p><p>\(f\prime(x) = \lim_{h\to0}\frac{f(x+h)-f(x)}{h}\)</p><script>alert("BAD SCRIPT")</script><script type="math/tex; mode=display">x^2</script><img alt="Slope of tangent"><a href="/next">Next lesson</a></main></html>'


def response(body=HTML.encode(), status=200, **headers):
    result = Mock(status=status)
    values = {'Content-Type': 'text/html; charset=utf-8', **headers}
    result.getheader.side_effect = lambda key, default=None: values.get(key, default)
    result.headers = Message()
    for key, value in values.items():
        result.headers[key] = value
    result.read1.side_effect = io.BytesIO(body).read1
    return result


class WebBoundaryTests(UnitTestCase):
    def test_url_rejections(self):
        for url in ('http://example.com', 'https://u:p@example.com', 'https://example.com:444/', 'https://127.0.0.1/', 'https://169.254.169.254/', 'https://localhost/', 'https://example.local/', 'https://[::1]/', 'https://example.com/\r\nHost:localhost', 'https://example.com\\@127.0.0.1'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                web.validate_url(url)
        self.assertEqual(web.validate_url('https://example.com:443/a#b'), 'https://example.com/a')

    def test_all_dns_answers_checked(self):
        private = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 443))
        with patch.object(socket, 'getaddrinfo', return_value=PUBLIC + [private]), self.assertRaises(ValueError):
            web.resolve_public('example.com', time.monotonic()+10)
        for address in ('192.0.0.8', '192.88.99.1', '64:ff9b::7f00:1', '3fff::1', '2001:20::1'):
            with self.subTest(address=address):
                self.assertFalse(web.public_address(web.ipaddress.ip_address(address)))

    def test_dns_timeout(self):
        import queue
        with patch.object(web.queue.Queue, 'get', side_effect=queue.Empty), self.assertRaisesRegex(ValueError, 'DNS lookup timed out'):
            web.resolve_public('example.com', time.monotonic()+10)

    def test_connect_pins_numeric_address_and_verifies_original_hostname(self):
        context, raw, tls = Mock(), Mock(), Mock()
        context.wrap_socket.return_value = tls
        with patch.object(web.ssl, 'create_default_context', return_value=context), patch.object(web.socket, 'socket', return_value=raw), patch.object(web.socket, 'getaddrinfo', side_effect=AssertionError('Second DNS lookup')):
            connection = web.PinnedHTTPSConnection('example.com', PUBLIC[0], time.monotonic()+20)
            connection.connect()
            raw.connect.assert_called_once_with(('93.184.216.34', 443))
            context.wrap_socket.assert_called_once_with(raw, server_hostname='example.com')
            connection.dispose()

    def test_wall_deadline_survives_connection_close_and_incomplete_chunks(self):
        for incomplete in (b'1', b'0\r\nX-Trailer: '):
            with self.subTest(incomplete=incomplete):
                client, server = socket.socketpair()
                client.settimeout(2)
                server.settimeout(2)
                connection = web.PinnedHTTPSConnection('example.com', PUBLIC[0], time.monotonic()+0.3)
                connection.sock = connection.raw_socket = connection.tls_socket = client
                connection.abort_socket = client.dup()
                connection.timer = threading.Timer(0.15, connection.abort)
                connection.timer.start()
                def serve():
                    server.recv(4096)
                    server.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\nTransfer-Encoding: chunked\r\nContent-Type: text/html\r\n\r\n'+incomplete)
                worker = threading.Thread(target=serve)
                worker.start()
                started = time.monotonic()
                try:
                    connection.request('GET', '/')
                    result = connection.getresponse()
                    self.assertIsNone(connection.sock)  # HTTPConnection already closed.
                    self.assertTrue(connection.timer.is_alive())
                    try:
                        web.read_body(result, time.monotonic()+1, lambda:False)
                    except (OSError, ValueError, web.http.client.HTTPException):
                        pass
                    self.assertLess(time.monotonic()-started, 0.9)
                    result.close()
                finally:
                    connection.dispose()
                    server.close()
                    worker.join(timeout=1)

    def test_redirect_is_revalidated_before_connect(self):
        with patch.object(web, 'resolve_public', return_value=PUBLIC[0]) as dns, patch.object(web, 'PinnedHTTPSConnection') as connection:
            connection.return_value.getresponse.return_value = response(status=302, Location='https://127.0.0.1/')
            with self.assertRaises(ValueError):
                web.fetch_html('https://example.com/')
            self.assertEqual(dns.call_count, 1)

    def test_redirect_dns_rebinding_and_redirect_limit(self):
        with patch.object(web, 'resolve_public', side_effect=[PUBLIC[0], ValueError('non-public')]), patch.object(web, 'PinnedHTTPSConnection') as connection:
            connection.return_value.getresponse.return_value = response(status=302, Location='/next')
            with self.assertRaisesRegex(ValueError, 'non-public'):
                web.fetch_html('https://example.com/')
            self.assertEqual(connection.call_count, 1)
        with patch.object(web, 'resolve_public', return_value=PUBLIC[0]), patch.object(web, 'PinnedHTTPSConnection') as connection:
            connection.return_value.getresponse.return_value = response(status=302, Location='/next')
            with self.assertRaisesRegex(ValueError, 'three redirects'):
                web.fetch_html('https://example.com/')
            self.assertEqual(connection.call_count, 4)

    def test_limits_compression_and_timeouts(self):
        for body, headers in [(b'a', {'Content-Length': str(web.MAX_WIRE+1)}), (b'a'*(web.MAX_WIRE+1), {}), (gzip.compress(b'a'*(web.MAX_HTML+1)), {'Content-Encoding':'gzip'}), (b'broken', {'Content-Encoding':'gzip'}), (b'a', {'Content-Encoding':'br'})]:
            with self.subTest(headers=headers), self.assertRaises((ValueError, web.zlib.error)):
                web.read_body(response(body, **headers), time.monotonic()+10, lambda:False)
        with self.assertRaises(ValueError):
            web.read_body(response(), time.monotonic()-1, lambda:False)
        self.assertEqual(web.read_body(response(gzip.compress(b'hello'), **{'Content-Encoding':'gzip'}), time.monotonic()+10, lambda:False), b'hello')

    def test_content_type_and_transport_errors(self):
        with patch.object(web, 'resolve_public', return_value=PUBLIC[0]), patch.object(web, 'PinnedHTTPSConnection') as connection:
            connection.return_value.getresponse.return_value = response(**{'Content-Type':'application/pdf'})
            with self.assertRaisesRegex(ValueError, 'HTML webpage'):
                web.fetch_html('https://example.com/')
            connection.return_value.getresponse.side_effect = socket.timeout()
            with self.assertRaisesRegex(ValueError, 'timed out'):
                web.fetch_html('https://example.com/')

    def test_math_article_links_and_malformed_html(self):
        text, title, main = web.extract_article(HTML, 'https://example.com/')
        self.assertTrue(main)
        self.assertEqual(title, 'Derivative lesson')
        for expected in ('# The derivative', r'\frac{f(x+h)-f(x)}{h}', r'\[x^2\]', 'Slope of tangent', 'https://example.com/next'):
            self.assertIn(expected, text)
        self.assertNotIn('UNWANTED MENU', text)
        self.assertNotIn('BAD SCRIPT', text)
        self.assertIn('rate of change', web.extract_article(HTML[:-30], 'https://example.com/')[0])
        with self.assertRaises(ValueError):
            web.extract_article('<html><script>nothing</script></html>', 'https://example.com/')

    def test_adversarial_parser_limits(self):
        for html in ('<article>'*10000+'a'*1000+'</article>'*10000, '<div>'*10000+'a'*1000, '<p>a</p>'*20000, '<main>'+'a'*500001+'</main>'):
            started = time.monotonic()
            with self.assertRaises(ValueError):
                web.extract_article(html, 'https://example.com/')
            self.assertLess(time.monotonic()-started, 3.5)

    def test_page_boundaries_preserve_tex_and_urls(self):
        equation = r'\[f\prime(x) = \frac{x^2+h}{h}' + '\n\n' + r'+ \lim_{h\to0}h\]'
        link = 'https://example.com/' + 'path'*300
        article = ('First paragraph. '*730) + '\n\n' + equation + '\n\n' + link + '\n\nEnd.'
        pages = web.split_article(article)
        self.assertGreater(len(pages), 1)
        self.assertEqual(''.join(pages), article)
        self.assertTrue(any(equation in page for page in pages))
        self.assertTrue(any(link in page for page in pages))
        self.assertEqual(web.split_article('x'*20000), ['x'*20000])
        with self.assertRaises(ValueError):
            web.split_article('x'*90001)


class WebImportTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=Path(self.temp.name)/'media', DATA_ROOT=Path(self.temp.name))
        self.override.enable()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.override.disable)
        self.client = APIClient()
        self.course = Course.objects.create(name='Calculus')

    def test_api_to_job_extraction_provenance_download_and_course_isolation(self):
        result = self.client.post('/api/sources/', {'course':self.course.id, 'url':'https://example.com/'}, format='json')
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data['status'], 'queued')
        with patch.object(web, 'fetch_html', return_value=(HTML.encode(), HTML, 'https://example.com/lesson')):
            run_job(claim('generation'))
        source = Source.objects.get(pk=result.data['id'])
        self.assertEqual(source.status, 'ready')
        self.assertEqual(source.title, 'Derivative lesson')
        self.assertEqual(len(source.digest), 64)
        self.assertIsNotNone(source.fetched_at)
        self.assertIn('JavaScript', source.extraction_notes)
        page = source.pages.get()
        self.assertIn('URL: https://example.com/lesson', page.text)
        self.assertFalse(page.image)
        other = Course.objects.create(name='Other')
        self.assertEqual(retrieve(other.id, 'derivative'), [])
        self.assertEqual(self.client.get(f'/api/sources/{source.id}/?course={other.id}').status_code, 404)
        download = self.client.get('/media/'+source.original.name)
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment', download['Content-Disposition'])
        self.assertIn('sandbox', download['Content-Security-Policy'])
        download.close()

    def test_failure_job_and_source_state_and_invalid_course(self):
        result = self.client.post('/api/sources/', {'course':self.course.id, 'url':'https://example.com/'}, format='json')
        with patch.object(web, 'fetch_html', side_effect=ValueError('Webpage hostname resolves to a non-public address.')):
            run_job(claim('generation'))
        source = Source.objects.get(pk=result.data['id'])
        self.assertEqual(source.status, 'error')
        self.assertIn('non-public', source.error)
        self.assertEqual(Job.objects.get(pk=result.data['job']['id']).status, 'failed')
        self.assertFalse(source.pages.exists())
        self.assertEqual(self.client.post('/api/sources/', {'course':999999, 'url':'https://example.com/'}, format='json').status_code, 404)
        self.assertEqual(self.client.post('/api/sources/', {'course':self.course.id, 'url':'https://localhost/'}, format='json').status_code, 400)
