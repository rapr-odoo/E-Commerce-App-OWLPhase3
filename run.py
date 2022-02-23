import json
import logging
import os
from werkzeug.serving import run_simple

import io
import hashlib
from lxml import etree
from collections import OrderedDict

from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.wrappers import Request, Response

_logger = logging.getLogger(__name__)

class ECommerceApp(object):
  NAME_TEMPLATE_DIRECTIVE = 't-name'

  def __init__(self):
    self.template_dict = OrderedDict()
    self.url_map = Map([
      Rule('/', endpoint='index'),
      Rule('/loadqweb', endpoint='loadQweb'),
    ])


  def dispatch_request(self, request, start_response):
    """Dispatches the request."""
    # print("In dispatch ::: ")
    # print(self, request.environ, sep='\n\n')

    adapter = self.url_map.bind_to_environ(request.environ)
    try:
        endpoint, values = adapter.match()
        response = getattr(self, endpoint)(request, **values)
        # return response(environ, start_response)
        return response
    except HTTPException as e:
        return e


  def wsgi_app(self, environ, start_response):
    """WSGI application that processes requests and returns responses."""
    # print("In __Wsgi__ ::: ")
    # print(self, environ, start_response, sep='\n\n')
    request = Request(environ)
    print(f"Request::: {request}")
    response = self.dispatch_request(request, start_response)
    return response(environ, start_response)


  def __call__(self, environ, start_response):
    """The WSGI server calls this method as the WSGI application."""
    # print("In __Call__ ::: ")
    # print(f"self:: {self}", f"environ::: {environ}", start_response, sep='\n\n')
    return self.wsgi_app(environ, start_response)


  def _compute_xml_tree(self, file_name, source):
    """Computes the xml tree that 'source' contains
    Applies inheritance specs in the process

    :param str addon: the current addon we are reading files for
    :param str file_name: the current name of the file we are reading
    :param str source: the content of the file
    :returns: etree
    """
    try:
        all_templates_tree = etree.parse(io.BytesIO(source), parser=etree.XMLParser(remove_comments=True)).getroot()
    except etree.ParseError as e:
        _logger.error("Could not parse file %s: %s" % (file_name, e.msg))
        raise e

    self.template_dict.setdefault(file_name, OrderedDict())
    for template_tree in list(all_templates_tree):
        if self.NAME_TEMPLATE_DIRECTIVE in template_tree.attrib:
            template_name = template_tree.attrib[self.NAME_TEMPLATE_DIRECTIVE]
        else:
            # self.template_dict[addon] grows after processing each template
            template_name = 'anonymous_template_%s' % len(self.template_dict[file_name])
        if template_name in self.template_dict[file_name]:
            # raise ValueError("Template %s already exists in file %s" % (template_name, file_name))
            return all_templates_tree
        self.template_dict[file_name][template_name] = template_tree
    return all_templates_tree

  def _concat_xml(self, fileList):
    """Concatenate xml files

    :param list fileList: list of files
    :returns: (concatenation_result, checksum)
    :rtype: (bytes, str)
    """
    checksum = hashlib.new('sha1')
    if not fileList:
        return b'', checksum.hexdigest()

    root = None
    for fname in fileList:
        contents = self._read_addon_file(fname)
        checksum.update(contents)
        # if not self.checksum_only: # TODO: MSH: keep temmplates in memory, no need to do concatination each time until and unless checksum is False
        xml = self._compute_xml_tree(fname, contents)

        if root is None:
            root = etree.Element(xml.tag)

    for file_name in self.template_dict.values():
        for template in file_name.values():
            root.append(template)

    return etree.tostring(root, encoding='utf-8') if root is not None else b''


  def _read_addon_file(self, file_path):
    """Reads the content of a file given by file_path
    Usefull to make 'self' testable
    :param str file_path:
    :returns: str
    """
    with open(file_path, 'rb') as fp:
      contents = fp.read()
    return contents

  def loadQweb(self, request):
    # TODO: MSH: Do not specify here which templates to load, create manifest file
    # where all templates are defined and read manifest file and load all templates
    # concanate all templates and return to client so client can call qweb.add_templates

    files = [
        "static/app/app.xml",
        "static/components/header/header.xml",
    ]

    # No need to use right now
    # concatedXml = self._concat_xml(files)
    concatedXml = self._concat_xml(files)
    concatedXml = concatedXml.decode("utf-8")

    # TODO: MSH: Develop server architecture so that it accepts both http and json request and return response accordingly
    response = {
        'jsonrpc': '2.0',
        # 'id': request.get('id')
    }
    mime = 'application/json'
    result = {'result': concatedXml}
    body = json.dumps(result)
    # return Response(concatedXml, mimetype='text/xml')
    return Response(
        body, status=200,
        headers=[('Content-Type', mime), ('Content-Length', len(body))]
    )


  def index(self, request):
    file_path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
    file_data = None
    with open(file_path, "rb") as fp:
      file_data = fp.read()
    return Response(file_data, content_type="text/html")


def create_app():
  app = ECommerceApp()
  return app


if __name__ == '__main__':
  # Run the Werkzeug development server to serve the WSGI application (MovieApp)
  app = create_app()
  app.wsgi_app = SharedDataMiddleware(
      app.wsgi_app, {"/static": os.path.join(os.path.dirname(__file__), "static")}
  )
  run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)