"""Single-page HTTPS extraction. No browser, proxy, cookies, or subresource requests."""
import hashlib
import io
import http.client
import ipaddress
import queue
import re
import socket
import ssl
import threading
import time
import zlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit, quote

MAX_WIRE = 2 * 1024 * 1024
MAX_HTML = 5 * 1024 * 1024
TOTAL_SECONDS = 30
# Python 3.10's bundled IANA tables predate these special-use classifications.
SPECIAL_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    '192.0.0.0/24', '192.88.99.0/24', '64:ff9b::/96', '64:ff9b:1::/48',
    '2001::/23', '2002::/16', '3fff::/20',
))
NOTES = ('Text extraction only. Equations retain source TeX or alternative text when available. '
         'Images, diagrams, styles, interactive content and JavaScript are not archived or reconstructed. '
         'Open the original page or upload its PDF for faithful visuals.')


def validate_url(value):
    if not isinstance(value, str) or not value or len(value) > 2048 or re.search(r'[\s\\\x00-\x1f\x7f]', value):
        raise ValueError('Provide an HTTPS webpage URL of at most 2,048 characters.')
    try:
        parts = urlsplit(value)
        host = (parts.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
        port = parts.port
    except (ValueError, UnicodeError):
        raise ValueError('Invalid webpage URL.') from None
    if parts.scheme != 'https' or not host or parts.username is not None or parts.password is not None or port not in (None, 443):
        raise ValueError('Use HTTPS on port 443 without credentials.')
    if '%' in host or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
        raise ValueError('Only public Internet hosts are allowed.')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[a-z0-9.-]+', host):
            raise ValueError('Invalid public hostname.') from None
    else:
        if not public_address(address):
            raise ValueError('Only public Internet addresses are allowed.')
    authority = f'[{host}]' if ':' in host else host
    path = quote(parts.path or '/', safe="/%:@!$&'()*+,;=-._~")
    query = quote(parts.query, safe="/%?:@!$&'()*+,;=-._~")
    return urlunsplit(('https', authority, path, query, ''))


def public_address(address):
    # Reject transition mechanisms as well as private/special-use address space.
    return (address.is_global and not address.is_multicast and not address.is_reserved
            and not any(address in network for network in SPECIAL_NETWORKS if address.version == network.version)
            and not getattr(address, 'ipv4_mapped', None)
            and not getattr(address, 'sixtofour', None) and not getattr(address, 'teredo', None))


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise ValueError('Webpage import exceeded its 30-second time limit.')
    return value


def resolve_public(host, deadline):
    results = queue.Queue(maxsize=1)
    def resolve():
        try:
            results.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except OSError:
            results.put(None)
    threading.Thread(target=resolve, daemon=True).start()
    try:
        answers = results.get(timeout=min(5, remaining(deadline)))
    except queue.Empty:
        raise ValueError('Webpage DNS lookup timed out.') from None
    if not answers:
        raise ValueError('Webpage hostname could not be resolved.')
    for answer in answers:
        if not public_address(ipaddress.ip_address(answer[4][0])):
            raise ValueError('Webpage hostname resolves to a non-public address.')
    return answers[0]


class DeadlineReader(io.RawIOBase):
    """Bound every socket read, including HTTP chunk framing and trailer reads."""
    def __init__(self, sock, deadline):
        self.sock, self.deadline = sock, deadline
        self.stream = sock.makefile('rb', buffering=0)
        self.received = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        self.sock.settimeout(min(8, remaining(self.deadline)))
        count = self.stream.readinto(buffer)
        self.received += count or 0
        if self.received > MAX_WIRE + 65536:
            raise ValueError('Webpage HTTP response exceeds its wire-size limit.')
        remaining(self.deadline)
        return count

    def close(self):
        self.stream.close()
        super().close()


class DeadlineSocket:
    def __init__(self, sock, deadline):
        self.sock, self.deadline = sock, deadline

    def makefile(self, mode):
        return io.BufferedReader(DeadlineReader(self.sock, self.deadline))


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a previously checked sockaddr, keeping normal TLS hostname verification."""
    def __init__(self, host, address, deadline):
        super().__init__(host, port=443, timeout=min(5, remaining(deadline)), context=ssl.create_default_context())
        self.address, self.deadline = address, deadline
        self.timer = None
        self.raw_socket = None
        self.tls_socket = None
        self.abort_socket = None
        self.response_class = lambda sock, **kwargs: http.client.HTTPResponse(DeadlineSocket(sock, deadline), **kwargs)

    def connect(self):
        family, kind, protocol, _, sockaddr = self.address
        raw = socket.socket(family, kind, protocol)
        self.raw_socket = raw
        raw.settimeout(min(5, remaining(self.deadline)))
        # A wall-clock deadline also bounds slow/dribbling headers and body reads.
        self.timer = threading.Timer(remaining(self.deadline), self.abort)
        self.timer.daemon = True
        self.timer.start()
        try:
            raw.connect(sockaddr)  # Numeric sockaddr: no second DNS lookup/rebinding.
            # A duplicate transport handle remains usable even when http.client
            # closes its socket object but a response file keeps the fd alive.
            self.abort_socket = raw.dup()
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
            self.tls_socket = self.sock
            self.sock.settimeout(min(8, remaining(self.deadline)))
        except Exception:
            self.dispose()
            raise

    def abort(self):
        for sock in (self.abort_socket, self.tls_socket, self.raw_socket):
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()

    def dispose(self):
        # HTTPConnection closes itself when response.will_close is true. Its
        # response file still owns the socket then, so retain the deadline until
        # the caller has finished reading the complete response (incl. trailers).
        if self.timer:
            self.timer.cancel()
        super().close()
        if self.tls_socket:
            self.tls_socket.close()
        if self.abort_socket:
            self.abort_socket.close()
        if self.raw_socket:
            self.raw_socket.close()


def read_body(response, deadline, cancelled):
    encoding = response.getheader('Content-Encoding', 'identity').lower().strip()
    if encoding not in ('identity', 'gzip', 'deflate'):
        raise ValueError('Unsupported webpage compression.')
    length = response.getheader('Content-Length')
    if length and (not length.isdigit() or int(length) > MAX_WIRE):
        raise ValueError('Webpage exceeds the 2 MB download limit.')
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS if encoding == 'gzip' else zlib.MAX_WBITS) if encoding != 'identity' else None
    result = bytearray()
    wire_size = 0
    while True:
        remaining(deadline)
        if cancelled():
            raise InterruptedError('Cancelled.')
        block = response.read1(65536)
        if not block:
            break
        wire_size += len(block)
        if wire_size > MAX_WIRE:
            raise ValueError('Webpage exceeds the 2 MB download limit.')
        result.extend(decoder.decompress(block, MAX_HTML + 1 - len(result)) if decoder else block)
        if len(result) > MAX_HTML or (decoder and decoder.unconsumed_tail):
            raise ValueError('Expanded webpage exceeds the 5 MB limit.')
    if decoder and (not decoder.eof or decoder.unused_data):
        raise ValueError('Invalid or concatenated compressed webpage.')
    return bytes(result)


def fetch_html(url, cancelled=lambda: False):
    deadline = time.monotonic() + TOTAL_SECONDS
    current = validate_url(url)
    try:
        for redirect in range(4):
            if cancelled():
                raise InterruptedError('Cancelled.')
            parts = urlsplit(current)
            address = resolve_public(parts.hostname, deadline)
            connection = PinnedHTTPSConnection(parts.hostname, address, deadline)
            response = None
            try:
                connection.request('GET', parts.path + ('?' + parts.query if parts.query else ''), headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 TLDR-local-study/1.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate', 'Connection': 'close'})
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    target = response.getheader('Location')
                    if redirect == 3 or not target:
                        raise ValueError('Webpage exceeded three redirects or has an invalid redirect.')
                    current = validate_url(urljoin(current, target))
                    continue
                if response.status != 200:
                    raise ValueError(f'Webpage server returned HTTP {response.status}.')
                content_type = response.getheader('Content-Type', '')
                if content_type.split(';', 1)[0].strip().lower() not in ('text/html', 'application/xhtml+xml'):
                    raise ValueError('URL must return an HTML webpage. Download and upload PDFs separately.')
                body = read_body(response, deadline, cancelled)
                charset = response.headers.get_content_charset() or 'utf-8'
                try:
                    html = body.decode(charset, errors='replace')
                except LookupError:
                    raise ValueError('Webpage declares an unsupported text encoding.') from None
                return body, html, current
            finally:
                if response is not None:
                    response.close()
                connection.dispose()
    except (OSError, http.client.HTTPException, zlib.error):
        raise ValueError('Webpage could not be downloaded securely or timed out. Check the URL and retry.') from None


class ArticleParser(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    BLOCK = {'p', 'div', 'section', 'li', 'ul', 'ol', 'table', 'tr', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url, self.stack, self.candidates, self.all_text = url, [], [], []
        self.title = []
        self.deadline = time.monotonic() + 3
        self.nodes, self.characters, self.landmarks = 0, 0, 0

    def check_budget(self):
        self.nodes += 1
        if self.nodes > 50000 or len(self.stack) > 128 or time.monotonic() > self.deadline:
            raise ValueError('Webpage HTML exceeds extraction complexity limits.')

    def emit(self, text):
        if any(frame['skip'] for frame in self.stack):
            return
        self.characters += len(text)
        if self.characters > 500000:
            raise ValueError('Extracted webpage exceeds 500,000 characters.')
        self.all_text.append(text)
        for frame in self.stack:
            if frame['buffer'] is not None:
                frame['buffer'].append(text)

    def handle_starttag(self, tag, attrs):
        self.check_budget()
        attrs = dict(attrs)
        math_script = tag == 'script' and attrs.get('type', '').lower().startswith('math/tex')
        skip = tag in {'style', 'nav', 'header', 'footer', 'form', 'iframe', 'noscript'} or (tag == 'script' and not math_script)
        label = (attrs.get('id', '') + ' ' + attrs.get('class', '')).lower()
        rank = 3 if tag == 'article' or re.search(r'\b(?:maincontent|main-content|contentmain)\b', label) else 2 if tag == 'main' or attrs.get('role') == 'main' else 0
        if rank:
            self.landmarks += 1
            if self.landmarks > 64 or sum(frame['buffer'] is not None for frame in self.stack) >= 8:
                raise ValueError('Webpage HTML has too many nested article landmarks.')
        frame = {'tag': tag, 'skip': skip, 'buffer': [] if rank else None, 'rank': rank, 'href': attrs.get('href'), 'math': math_script, 'display': 'mode=display' in attrs.get('type', '')}
        self.stack.append(frame)
        if tag in self.BLOCK:
            self.emit('\n' + ('#' * int(tag[1]) + ' ' if re.fullmatch('h[1-6]', tag) else ''))
        if math_script:
            self.emit('\n\\[' if 'mode=display' in attrs.get('type', '') else '\\(')
        if tag == 'img':
            alt = attrs.get('alt', '').strip()
            if alt:
                self.emit(' [Image alternative text: ' + alt + '] ')
        if tag in self.VOID:
            self.stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self.check_budget()
        index = next((i for i in range(len(self.stack)-1, -1, -1) if self.stack[i]['tag'] == tag), None)
        if index is None:
            return
        frame = self.stack[index]
        if frame['math']:
            self.emit('\\]\n' if frame['display'] else '\\)\n')
        if tag == 'a' and frame['href']:
            target = urljoin(self.url, frame['href'])
            if urlsplit(target).scheme in ('https', 'http'):
                self.emit(' (' + target + ') ')
        if tag in self.BLOCK:
            self.emit('\n')
        for closing in self.stack[index:]:
            if closing['buffer'] is not None:
                self.candidates.append((closing['rank'], ''.join(closing['buffer'])))
        del self.stack[index:]

    def handle_data(self, data):
        self.check_budget()
        if any(frame['tag'] == 'title' for frame in self.stack):
            self.title.append(data)
        self.emit(data)


def extract_article(html, url):
    parser = ArticleParser(url)
    try:
        parser.feed(html)
        parser.close()
        while parser.stack:
            parser.handle_endtag(parser.stack[-1]['tag'])
    except (ValueError, RecursionError):
        raise ValueError('Webpage HTML could not be extracted.') from None
    candidates = [(rank, value) for rank, value in parser.candidates if len(value.strip()) >= 80]
    selected = max(candidates, key=lambda item: (item[0], len(item[1])))[1] if candidates else ''.join(parser.all_text)
    text = re.sub(r'[ \t\r\f\v]+', ' ', selected)
    text = re.sub(r'\n\s*\n+', '\n\n', text).strip()
    if len(text) < 80:
        raise ValueError('The webpage contains too little extractable text. Try a PDF or pasted notes.')
    if len(text) > 500000:
        raise ValueError('Extracted webpage exceeds 500,000 characters.')
    return text, re.sub(r'\s+', ' ', ''.join(parser.title)).strip()[:240], bool(candidates)


def split_article(text, target=12000):
    """Keep paragraphs, links and paired TeX intact; reject huge atomic blocks."""
    blocks, start, math_end = [], 0, None
    for token in re.finditer(r'\\[\[\]()]|(?<!\\)\$\$|(?<!\\)\$|\n[ \t]*\n+', text):
        value = token.group()
        if math_end is not None:
            if value == math_end:
                math_end = None
        elif value in (r'\[', r'\(', '$$', '$'):
            math_end = {r'\[':r'\]', r'\(':r'\)', '$$':'$$', '$':'$'}[value]
        elif value.startswith('\n'):
            blocks.append(text[start:token.end()])
            start = token.end()
    if start < len(text):
        blocks.append(text[start:])
    pages, current = [], ''
    for block in blocks:
        if len(block) > 90000:
            raise ValueError('A webpage paragraph or equation exceeds 90,000 characters. Upload a PDF or shorter notes.')
        if current and len(current) + len(block) > target:
            pages.append(current)
            current = ''
        current += block
    if current:
        pages.append(current)
    return pages


def ingest_web(source, cancelled):
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from .ingestion import make_page, clear_pages
    body, html, final_url = fetch_html(source.source_url, cancelled)
    text, title, main_found = extract_article(html, final_url)
    chunks = split_article(text)
    if cancelled():
        raise InterruptedError('Cancelled.')
    if source.original:
        source.original.delete(save=False)
    source.original.save('webpage.html', ContentFile(body), save=False)
    source.digest = hashlib.sha256(body).hexdigest()
    source.fetched_url, source.fetched_at = final_url, timezone.now()
    if title and source.title == source.source_url[:240]:
        source.title = title
    source.extraction_notes = NOTES + ('' if main_found else ' No main article landmark was found; surrounding page text may be included.')
    source.save()
    clear_pages(source)
    attribution = f'Source: {source.title}\nURL: {final_url}\nFetched: {source.fetched_at.isoformat()}\n\n'
    for number, chunk in enumerate(chunks, 1):
        if cancelled():
            raise InterruptedError('Cancelled.')
        make_page(source, number, attribution + chunk)
    source.status, source.error = 'ready', ''
    source.save(update_fields=['status', 'error'])
