from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from pytest import raises

from aspen import dispatcher, Response
from aspen.http.request import Request
from aspen.testing import handle, NoException, StubRequest
from aspen.testing import fix

# Helpers
# =======

def assert_raises_404(func, *args):
    response = raises(Response, func, *args).value
    assert response.code == 404
    return response

def assert_raises_302(func, *args):
    response = raises(Response, func, *args).value
    assert response.code == 302
    return response

def check(path, *a):
    """Given a URI path, return a dispatched request object.
    """
    request = StubRequest.from_fs(path.encode('ascii'), *a)
    dispatcher.dispatch(request)
    return request


# Indices
# =======

def test_index_is_found(mk):
    mk(('index.html', "Greetings, program!"))
    expected = fix('index.html')
    actual = check('/').fs
    assert actual == expected

def test_negotiated_index_is_found(mk):
    mk(( 'index'
       , """
[----------] text/html
<h1>Greetings, program!</h1>
[----------] text/plain
Greetings, program!
"""))
    expected = fix('index')
    actual = check('/').fs
    assert actual == expected

def test_alternate_index_is_not_found(mk):
    mk(('default.html', "Greetings, program!"))
    assert_raises_404(check, '/')

def test_alternate_index_is_found(mk):
    mk( ('.aspen/configure-aspen.py', 'website.indices += ["default.html"]')
      , ('default.html', "Greetings, program!")
       )
    expected = fix('default.html')
    actual = check('/').fs
    assert actual == expected

def test_configure_aspen_py_setting_override_works_too(mk):
    mk( ('.aspen/configure-aspen.py', 'website.indices = ["default.html"]')
      , ('index.html', "Greetings, program!")
       )
    assert_raises_404(check, '/')

def test_configure_aspen_py_setting_takes_first(mk):
    mk( ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('index.html', "Greetings, program!")
      , ('default.html', "Greetings, program!")
       )
    expected = fix('index.html')
    actual = check('/').fs
    assert actual == expected

def test_configure_aspen_py_setting_takes_second_if_first_is_missing(mk):
    mk( ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('default.html', "Greetings, program!")
       )
    expected = fix('default.html')
    actual = check('/').fs
    assert actual == expected

def test_configure_aspen_py_setting_strips_commas(mk):
    mk( ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('default.html', "Greetings, program!")
       )
    expected = fix('default.html')
    actual = check('/').fs
    assert actual == expected

def test_redirect_indices_to_slash(mk):
    mk( ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('index.html', "Greetings, program!")
       )
    assert_raises_302(check, '/index.html')

def test_redirect_second_index_to_slash(mk):
    mk( ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('default.html', "Greetings, program!")
       )
    assert_raises_302(check, '/default.html')

def test_dont_redirect_second_index_if_first(mk):
    mk( ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('default.html', "Greetings, program!")
      , ('index.html', "Greetings, program!")
       )
    # first index redirects
    assert_raises_302(check, '/index.html')
    # second shouldn't
    expected = fix('default.html')
    actual = check('/default.html').fs
    assert actual == expected


# Negotiated Fall-through
# =======================

def test_indirect_negotiation_can_passthrough_renderered(mk):
    mk(('foo.html', "Greetings, program!"))
    expected = fix('foo.html')
    actual = check('foo.html').fs
    assert actual == expected

def test_indirect_negotiation_can_passthrough_negotiated(mk):
    mk(('foo', "Greetings, program!"))
    expected = fix('foo')
    actual = check('foo').fs
    assert actual == expected

def test_indirect_negotiation_modifies_one_dot(mk):
    mk(('foo', "Greetings, program!"))
    expected = fix('foo')
    actual = check('foo.html').fs
    assert actual == expected

def test_indirect_negotiation_skips_two_dots(mk):
    mk(('foo.bar', "Greetings, program!"))
    expected = fix('foo.bar')
    actual = check('foo.bar.html').fs
    assert actual == expected

def test_indirect_negotiation_prefers_rendered(mk):
    mk( ('foo.html', "Greetings, program!")
      , ('foo', "blah blah blah")
       )
    expected = fix('foo.html')
    actual = check('foo.html').fs
    assert actual == expected

def test_indirect_negotiation_really_prefers_rendered(mk):
    mk( ('foo.html', "Greetings, program!")
      , ('foo.', "blah blah blah")
       )
    expected = fix('foo.html')
    actual = check('foo.html').fs
    assert actual == expected

def test_indirect_negotiation_really_prefers_rendered_2(mk):
    mk( ('foo.html', "Greetings, program!")
      , ('foo', "blah blah blah")
       )
    expected = fix('foo.html')
    actual = check('foo.html').fs
    assert actual == expected

def test_indirect_negotation_doesnt_do_dirs(mk):
    mk(('foo/bar.html', "Greetings, program!"))
    assert_raises_404(check, 'foo.html')


# Virtual Paths
# =============

def test_virtual_path_can_passthrough(mk):
    mk(('foo.html', "Greetings, program!"))
    expected = fix('foo.html')
    actual = check('foo.html').fs
    assert actual == expected

def test_unfound_virtual_path_passes_through(mk):
    mk(('%bar/foo.html', "Greetings, program!"))
    assert_raises_404(check, '/blah/flah.html')

def test_virtual_path_is_virtual(mk):
    mk(('%bar/foo.html', "Greetings, program!"))
    expected = fix('%bar/foo.html')
    actual = check('/blah/foo.html').fs
    assert actual == expected

def test_virtual_path_sets_request_path(mk):
    mk(('%bar/foo.html', "Greetings, program!"))
    expected = {'bar': [u'blah']}
    actual = check('/blah/foo.html').line.uri.path
    assert actual == expected

def test_virtual_path_sets_unicode_request_path(mk):
    mk(('%bar/foo.html', "Greetings, program!"))
    expected = {'bar': [u'\u2603']}
    actual = check('/%E2%98%83/foo.html').line.uri.path
    assert actual == expected

def test_virtual_path_typecasts_to_int(mk):
    mk(('%year.int/foo.html', "Greetings, program!"))
    expected = {'year': [1999]}
    actual = check('/1999/foo.html').line.uri.path
    assert actual == expected

def test_virtual_path_raises_on_bad_typecast(mk):
    mk(('%year.int/foo.html', "Greetings, program!"))
    raises(Response, check, '/I am not a year./foo.html')

def test_virtual_path_raises_404_on_bad_typecast(mk):
    mk(('%year.int/foo.html', "Greetings, program!"))
    assert_raises_404(check, '/I am not a year./foo.html')

def test_virtual_path_raises_on_direct_access(mk):
    mk()
    raises(Response, check, '/%name/foo.html')

def test_virtual_path_raises_404_on_direct_access(mk):
    mk()
    assert_raises_404(check, '/%name/foo.html')

def test_virtual_path_matches_the_first(mk):
    mk( ('%first/foo.html', "Greetings, program!")
      , ('%second/foo.html', "WWAAAAAAAAAAAA!!!!!!!!")
       )
    expected = fix('%first/foo.html')
    actual = check('/1999/foo.html').fs
    assert actual == expected

def test_virtual_path_directory(mk):
    mk(('%first/index.html', "Greetings, program!"))
    expected = fix('%first/index.html')
    actual = check('/foo/').fs
    assert actual == expected

def test_virtual_path_file(mk):
    mk(('foo/%bar.html.spt', "Greetings, program!"))
    expected = fix('foo/%bar.html.spt')
    actual = check('/foo/blah.html').fs
    assert actual == expected

def test_virtual_path_file_only_last_part(mk):
    mk(('foo/%bar.html.spt', "Greetings, program!"))
    expected = fix('foo/%bar.html.spt')
    actual = check('/foo/blah/baz.html').fs
    assert actual == expected

def test_virtual_path_file_only_last_part____no_really(mk):
    mk(('foo/%bar.html', "Greetings, program!"))
    assert_raises_404(check, '/foo/blah.html/')

def test_virtual_path_file_key_val_set(mk):
    mk(('foo/%bar.html.spt', "Greetings, program!"))
    expected = {'bar': [u'blah']}
    actual = check('/foo/blah.html').line.uri.path
    assert actual == expected

def test_virtual_path_file_key_val_not_cast(mk):
    mk(('foo/%bar.html.spt', "Greetings, program!"))
    expected = {'bar': [u'537']}
    actual = check('/foo/537.html').line.uri.path
    assert actual == expected

def test_virtual_path_file_key_val_cast(mk):
    mk(('foo/%bar.int.html.spt', "Greetings, program!"))
    expected = {'bar': [537]}
    actual = check('/foo/537.html').line.uri.path
    assert actual == expected

def test_virtual_path_file_not_dir(mk):
    mk( ('%foo/bar.html', "Greetings from bar!")
      , ('%baz.html.spt', "Greetings from baz!")
       )
    expected = fix('%baz.html.spt')
    actual = check('/bal.html').fs
    assert actual == expected


# negotiated *and* virtual paths
# ==============================

def test_virtual_path__and_indirect_neg_file_not_dir(mk):
    mk( ('%foo/bar.html', "Greetings from bar!")
      , ('%baz.spt', "Greetings from baz!")
       )
    expected = fix('%baz.spt')
    actual = check('/bal.html').fs
    assert actual == expected

def test_virtual_path_and_indirect_neg_noext(mk):
    mk( ('%foo/bar', "Greetings program!"))
    actual = check('/greet/bar').fs
    expected = fix('%foo/bar')
    assert actual == expected

def test_virtual_path_and_indirect_neg_ext(mk):
    mk( ('%foo/bar', "Greetings program!"))
    actual = check('/greet/bar.html').fs
    expected = fix('%foo/bar')
    assert actual == expected


# trailing slash
# ==============

def test_dispatcher_passes_through_files(mk):
    mk(('foo/index.html', "Greetings, program!"))
    assert_raises_404(check, '/foo/537.html')

def test_trailing_slash_passes_dirs_with_slash_through(mk):
    mk(('foo/index.html', "Greetings, program!"))
    expected = fix('/foo/index.html')
    actual = check('/foo/').fs
    assert actual == expected

def test_dispatcher_passes_through_virtual_dir_with_trailing_slash(mk):
    mk(('%foo/index.html', "Greetings, program!"))
    expected = fix('/%foo/index.html')
    actual = check('/foo/').fs
    assert actual == expected

def test_dispatcher_redirects_dir_without_trailing_slash(mk):
    mk('foo')
    response = raises(Response, check, '/foo').value
    expected = (302, '/foo/')
    actual = (response.code, response.headers['Location'])
    assert actual == expected

def test_dispatcher_redirects_virtual_dir_without_trailing_slash(mk):
    mk('%foo')
    response = raises(Response, check, '/foo').value
    expected = (302, '/foo/')
    actual = (response.code, response.headers['Location'])
    assert actual == expected

def test_trailing_on_virtual_paths_missing(mk):
    mk('%foo/%bar/%baz')
    response = raises(Response, check, '/foo/bar/baz').value
    expected = '/foo/bar/baz/'
    actual = response.headers['Location']
    assert actual == expected

def test_trailing_on_virtual_paths(mk):
    mk(('%foo/%bar/%baz/index.html', "Greetings program!"))
    expected = fix('/%foo/%bar/%baz/index.html')
    actual = check('/foo/bar/baz/').fs
    assert actual == expected

def test_dont_confuse_files_for_dirs(mk):
    mk( ('foo.html', 'Greetings, Program!') )
    response = raises(Response, check, '/foo.html/bar').value
    assert response.code == 404



# path part params
# ================

def test_path_part_with_params_works(mk):
    mk(('foo/index.html', "Greetings program!"))
    expected = fix('/foo/index.html')
    actual = check('/foo;a=1/').fs
    assert actual == expected

def test_path_part_params_vpath(mk):
    mk(('%bar/index.html', "Greetings program!"))
    expected = fix('/%bar/index.html')
    actual = check('/foo;a=1;b=;a=2;b=3/').fs
    assert actual == expected

def test_path_part_params_static_file(mk):
    mk(('/foo/bar.html', "Greetings program!"))
    expected = fix('/foo/bar.html')
    actual = check('/foo/bar.html;a=1;b=;a=2;b=3').fs
    assert actual == expected

def test_path_part_params_simplate(mk):
    mk(('/foo/bar.html.spt', "Greetings program!"))
    expected = fix('/foo/bar.html.spt')
    actual = check('/foo/bar.html;a=1;b=;a=2;b=3').fs
    assert actual == expected

def test_path_part_params_negotiated_simplate(mk):
    mk(('/foo/bar.spt', "Greetings program!"))
    expected = fix('/foo/bar.spt')
    actual = check('/foo/bar.html;a=1;b=;a=2;b=3').fs
    assert actual == expected

def test_path_part_params_greedy_simplate(mk):
    mk(('/foo/%bar.spt', "Greetings program!"))
    expected = fix('/foo/%bar.spt')
    actual = check('/foo/baz/buz;a=1;b=;a=2;b=3/blam.html').fs
    assert actual == expected


# Docs
# ====

GREETINGS_NAME_SPT = "[-----]\nname = path['name']\n[------]\nGreetings, %(name)s!"

def test_virtual_path_docs_1(mk):
    mk(('%name/index.html.spt', GREETINGS_NAME_SPT))
    expected = "Greetings, aspen!"
    response = handle('/aspen/')
    actual = response.body
    assert actual == expected

def test_virtual_path_docs_2(mk):
    mk(('%name/index.html.spt', GREETINGS_NAME_SPT))
    expected = "Greetings, python!"
    response = handle('/python/')
    actual = response.body
    assert actual == expected

NAME_LIKES_CHEESE_SPT = "name = path['name'].title()\ncheese = path['cheese']\n[---------]\n%(name)s likes %(cheese)s cheese."

def test_virtual_path_docs_3(mk):
    mk( ( '%name/index.html.spt', GREETINGS_NAME_SPT),
        ( '%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT)
      )
    response = handle('/chad/cheddar.txt')
    expected = "Chad likes cheddar cheese."
    actual = response.body
    assert actual == expected

def test_virtual_path_docs_4(mk):
    mk( ( '%name/index.html.spt', GREETINGS_NAME_SPT),
        ( '%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT)
       )
    response = handle('/chad/cheddar.txt/')
    expected = 404
    actual = response.code
    assert actual == expected

PARTY_LIKE_YEAR_SPT = "year = path['year']\n[----------]\nTonight we're going to party like it's %(year)s!"

def test_virtual_path_docs_5(mk):
    mk( ( '%name/index.html.spt', GREETINGS_NAME_SPT),
        ( '%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT),
        ( '%year.int/index.html.spt', PARTY_LIKE_YEAR_SPT)
       )
    response = handle('/1999/')
    expected = "Greetings, 1999!"
    actual = response.body
    assert actual == expected

def test_virtual_path_docs_6(mk):
    mk( ( '%year.int/index.html.spt', PARTY_LIKE_YEAR_SPT))
    response = handle('/1999/')
    expected = "Tonight we're going to party like it's 1999!"
    actual = response.body
    assert actual == expected


# intercept_socket
# ================

def test_intercept_socket_protects_direct_access():
    request = Request(uri="/foo.sock")
    raises(Response, dispatcher.dispatch, request)

def test_intercept_socket_intercepts_handshake():
    request = Request(uri="/foo.sock/1")
    actual = dispatcher.extract_socket_info(request.line.uri.path.decoded)
    expected = ('/foo.sock', '1')
    assert actual == expected

def test_intercept_socket_intercepts_transported():
    request = Request(uri="/foo.sock/1/websocket/46327hfjew3?foo=bar")
    actual = dispatcher.extract_socket_info(request.line.uri.path.decoded)
    expected = ('/foo.sock', '1/websocket/46327hfjew3')
    assert actual == expected


# mongs
# =====
# These surfaced when porting mongs from Aspen 0.8.

def test_virtual_path_parts_can_be_empty(mk):
    mk(('foo/%bar/index.html.spt', "Greetings, program!"))
    expected = {u'bar': [u'']}
    actual = check('/foo//').line.uri.path
    assert actual == expected

def test_file_matches_in_face_of_dir(mk):
    mk( ('%page/index.html.spt', 'Nothing to see here.')
      , ('%value.txt.spt', "Greetings, program!")
       )
    expected = {'value': [u'baz']}
    actual = check('/baz.txt').line.uri.path
    assert actual == expected

def test_file_matches_extension(mk):
    mk( ('%value.json.spt', '{"Greetings,": "program!"}')
      , ('%value.txt.spt', "Greetings, program!")
       )
    expected = "%value.json.spt"
    actual = os.path.basename(check('/baz.json').fs)
    assert actual == expected

def test_file_matches_other_extension(mk):
    mk( ('%value.json.spt', '{"Greetings,": "program!"}')
      , ('%value.txt.spt', "Greetings, program!")
       )
    expected = "%value.txt.spt"
    actual = os.path.basename(check('/baz.txt').fs)
    assert actual == expected

def test_virtual_file_with_no_extension_works(mk):
    mk(('%value.spt', '{"Greetings,": "program!"}'))
    check('/baz.txt')
    assert NoException

def test_normal_file_with_no_extension_works(mk):
    mk( ('%value.spt', '{"Greetings,": "program!"}')
      , ('value', '{"Greetings,": "program!"}')
       )
    check('/baz.txt')
    assert NoException

def test_file_with_no_extension_matches(mk):
    mk( ('%value.spt', '{"Greetings,": "program!"}')
      , ('value', '{"Greetings,": "program!"}')
       )
    expected = {'value': [u'baz']}
    actual = check('/baz').line.uri.path
    assert actual == expected

def test_aspen_favicon_doesnt_get_clobbered_by_virtual_path(mk):
    mk('%value.spt')
    request = StubRequest.from_fs('/favicon.ico')
    dispatcher.dispatch(request)
    expected = {}
    actual = request.line.uri.path
    assert actual == expected

def test_robots_txt_also_shouldnt_be_redirected(mk):
    mk('%value.spt')
    request = StubRequest.from_fs('/robots.txt')
    err = raises(Response, dispatcher.dispatch, request).value
    actual = err.code
    assert actual == 404


