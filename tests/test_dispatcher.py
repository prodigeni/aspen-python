from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from pytest import raises

from aspen.website import Website
from aspen import dispatcher, Response
from aspen.http.request import Request
from aspen.testing import NoException, StubRequest

from aspen.testing.client import basic


# Helpers
# =======

from conftest import pymk

def handle(www_root, uri):
    """Given a www_root, return a response for uri"""
    tc = basic(str(www_root))
    result = tc.get(str(uri))
    return result

def assert_raises_404(www_root, uri):
    response = handle(www_root, uri)
    assert response.code == 404
    return response

def assert_raises_302(www_root, uri):
    response = handle(www_root, uri)
    assert response.code == 302
    return response

def check(www_root, uri):
    """Given a www_root, return a request for uri"""
    #return handle(www_root, uri).request
    request = StubRequest(str(uri))
    request.website = Website([ '--www_root', str(www_root)
                      , '--project_root', os.path.join(str(www_root), '.aspen')
                      ] )
    dispatcher.dispatch(request)
    return request

# Indices
# =======

def test_index_is_found(tmpdir):
    expected = pymk(tmpdir, ('index.html', 'Greetings, program!'))[0]
    actual = check(tmpdir, "/").fs
    assert actual == expected

def test_negotiated_index_is_found(tmpdir):
    expected = tmpdir.join('index')
    expected.write("""
[----------] text/html
<h1>Greetings, program!</h1>
[----------] text/plain
Greetings, program!
""")
    actual = check(tmpdir, '/').fs
    assert actual == expected

def test_alternate_index_is_not_found(tmpdir):
    tmpdir.join('default.html').write("Greetings, program!")
    assert_raises_404(tmpdir, '/')

def test_alternate_index_is_found(tmpdir):
    tmpdir.join('default.html').write("Greetings, program!")
    tmpdir.ensure('.aspen/configure-aspen.py').write('website.indices += ["default.html"]')
    expected = tmpdir.join('default.html')
    actual = check(tmpdir, '/').fs
    assert actual == expected

def test_configure_aspen_py_setting_override_works_too(tmpdir):
    tmpdir.join('index.html').write("Greetings, program!")
    tmpdir.ensure('.aspen/configure-aspen.py').write('website.indices = ["default.html"]')
    assert_raises_404(tmpdir, '/')

def test_configure_aspen_py_setting_takes_first(tmpdir):
    tmpdir.ensure('.aspen/configure-aspen.py').write('website.indices = ["index.html", "default.html"]')
    tmpdir.join('default.html').write("Greetings, program!")
    expected = tmpdir.join('index.html')
    expected.write("Greetings, program!")
    actual = check(tmpdir, '/').fs
    assert actual == expected

def test_configure_aspen_py_setting_takes_second_if_first_is_missing(tmpdir):
    tmpdir.ensure('.aspen/configure-aspen.py').write('website.indices = ["index.html", "default.html"]')
    expected = tmpdir.join('default.html')
    expected.write("Greetings, program!")
    actual = check(tmpdir, '/').fs
    assert actual == expected

def test_configure_aspen_py_setting_strips_commas(tmpdir):
    tmpdir.ensure('.aspen/configure-aspen.py').write('website.indices = ["index.html", "default.html"]')
    expected = tmpdir.join('default.html')
    expected.write("Greetings, program!")
    actual = check(tmpdir, '/').fs
    assert actual == expected

def test_redirect_indices_to_slash(tmpdir):
    pymk(tmpdir,
        ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('index.html', "Greetings, program!")
       )
    assert_raises_302(tmpdir, '/index.html')

def test_redirect_second_index_to_slash(tmpdir):
    pymk(tmpdir,
        ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('default.html', "Greetings, program!")
       )
    assert_raises_302(tmpdir, '/default.html')

def test_dont_redirect_second_index_if_first(tmpdir):
    pymk(tmpdir,
        ( '.aspen/configure-aspen.py'
        , 'website.indices = ["index.html", "default.html"]')
      , ('default.html', "Greetings, program!")
      , ('index.html', "Greetings, program!")
       )
    # first index redirects
    assert_raises_302(tmpdir, '/index.html')
    # second shouldn't
    expected = tmpdir.join('default.html')
    actual = check(tmpdir, '/default.html').fs
    assert actual == expected


# Negotiated Fall-through
# =======================

def test_indirect_negotiation_can_passthrough_renderered(tmpdir):
    pymk(tmpdir, ('foo.html', "Greetings, program!"))
    expected = tmpdir.join('foo.html')
    actual = check(tmpdir, 'foo.html').fs
    assert actual == expected

def test_indirect_negotiation_can_passthrough_negotiated(tmpdir):
    expected = pymk(tmpdir, ('foo', "Greetings, program!"))[0]
    actual = check(tmpdir, 'foo').fs
    assert actual == expected

def test_indirect_negotiation_modifies_one_dot(tmpdir):
    expected = pymk(tmpdir, ('foo', "Greetings, program!"))[0]
    actual = check(tmpdir, 'foo.html').fs
    assert actual == expected

def test_indirect_negotiation_skips_two_dots(tmpdir):
    expected = pymk(tmpdir, ('foo.bar', "Greetings, program!"))[0]
    actual = check(tmpdir, 'foo.bar.html').fs
    assert actual == expected

def test_indirect_negotiation_prefers_rendered(tmpdir):
    pymk(tmpdir,
        ('foo.html', "Greetings, program!")
      , ('foo', "blah blah blah")
       )
    expected = tmpdir.join('foo.html')
    actual = check(tmpdir, 'foo.html').fs
    assert actual == expected

def test_indirect_negotiation_really_prefers_rendered(tmpdir):
    pymk(tmpdir,
        ('foo.html', "Greetings, program!")
      , ('foo.', "blah blah blah")
       )
    expected = tmpdir.join('foo.html')
    actual = check(tmpdir, 'foo.html').fs
    assert actual == expected

def test_indirect_negotiation_really_prefers_rendered_2(tmpdir):
    pymk(tmpdir,
        ('foo.html', "Greetings, program!")
      , ('foo', "blah blah blah")
       )
    expected = tmpdir.join('foo.html')
    actual = check(tmpdir, 'foo.html').fs
    assert actual == expected

def test_indirect_negotation_doesnt_do_dirs(tmpdir):
    pymk(tmpdir, ('foo/bar.html', "Greetings, program!"))
    assert_raises_404(tmpdir, 'foo.html')


# Virtual Paths
# =============

def test_virtual_path_can_passthrough(tmpdir):
    pymk(tmpdir, ('foo.html', "Greetings, program!"))
    expected = tmpdir.join('foo.html')
    actual = check(tmpdir, 'foo.html').fs
    assert actual == expected

def test_unfound_virtual_path_passes_through(tmpdir):
    pymk(tmpdir, ('%bar/foo.html', "Greetings, program!"))
    assert_raises_404(tmpdir, '/blah/flah.html')

def test_virtual_path_is_virtual(tmpdir):
    pymk(tmpdir, ('%bar/foo.html', "Greetings, program!"))
    expected = tmpdir.join('%bar/foo.html')
    actual = check(tmpdir, '/blah/foo.html').fs
    assert actual == expected

def test_virtual_path_sets_request_path(tmpdir):
    pymk(tmpdir, ('%bar/foo.html', "Greetings, program!"))
    expected = {'bar': [u'blah']}
    actual = check(tmpdir, '/blah/foo.html').line.uri.path
    assert actual == expected

def test_virtual_path_sets_unicode_request_path(tmpdir):
    pymk(tmpdir, ('%bar/foo.html', "Greetings, program!"))
    expected = {'bar': [u'\u2603']}
    actual = check(tmpdir, '/%E2%98%83/foo.html').line.uri.path
    assert actual == expected

def test_virtual_path_typecasts_to_int(tmpdir):
    pymk(tmpdir, ('%year.int/foo.html', "Greetings, program!"))
    expected = {'year': [1999]}
    actual = check(tmpdir, '/1999/foo.html').line.uri.path
    assert actual == expected

def test_virtual_path_raises_on_bad_typecast(tmpdir):
    pymk(tmpdir, ('%year.int/foo.html', "Greetings, program!"))
    assert_raises_404(tmpdir, '/I am not a year./foo.html')
    #raises(Response, check, tmpdir, '/I am not a year./foo.html')

def test_virtual_path_raises_404_on_bad_typecast(tmpdir):
    pymk(tmpdir, ('%year.int/foo.html', "Greetings, program!"))
    assert_raises_404(tmpdir, '/I am not a year./foo.html')

def test_virtual_path_raises_on_direct_access(tmpdir):
    assert_raises_404(tmpdir, '/%name/foo.html')

def test_virtual_path_raises_404_on_direct_access(tmpdir):
    assert_raises_404(tmpdir, '/%name/foo.html')

def test_virtual_path_matches_the_first(tmpdir):
    pymk(tmpdir,
        ('%first/foo.html', "Greetings, program!")
      , ('%second/foo.html', "WWAAAAAAAAAAAA!!!!!!!!")
       )
    expected = tmpdir.join('%first/foo.html')
    actual = check(tmpdir, '/1999/foo.html').fs
    assert actual == expected

def test_virtual_path_directory(tmpdir):
    pymk(tmpdir, ('%first/index.html', "Greetings, program!"))
    expected = tmpdir.join('%first/index.html')
    actual = check(tmpdir, '/foo/').fs
    assert actual == expected

def test_virtual_path_file(tmpdir):
    pymk(tmpdir, ('foo/%bar.html.spt', "Greetings, program!"))
    expected = tmpdir.join('foo/%bar.html.spt')
    actual = check(tmpdir, '/foo/blah.html').fs
    assert actual == expected

def test_virtual_path_file_only_last_part(tmpdir):
    pymk(tmpdir, ('foo/%bar.html.spt', "Greetings, program!"))
    expected = tmpdir.join('foo/%bar.html.spt')
    actual = check(tmpdir, '/foo/blah/baz.html').fs
    assert actual == expected

def test_virtual_path_file_only_last_part____no_really(tmpdir):
    pymk(tmpdir, ('foo/%bar.html', "Greetings, program!"))
    assert_raises_404(tmpdir, '/foo/blah.html/')

def test_virtual_path_file_key_val_set(tmpdir):
    pymk(tmpdir, ('foo/%bar.html.spt', "Greetings, program!"))
    expected = {'bar': [u'blah']}
    actual = check(tmpdir, '/foo/blah.html').line.uri.path
    assert actual == expected

def test_virtual_path_file_key_val_not_cast(tmpdir):
    pymk(tmpdir, ('foo/%bar.html.spt', "Greetings, program!"))
    expected = {'bar': [u'537']}
    actual = check(tmpdir, '/foo/537.html').line.uri.path
    assert actual == expected

def test_virtual_path_file_key_val_cast(tmpdir):
    pymk(tmpdir, ('foo/%bar.int.html.spt', "Greetings, program!"))
    expected = {'bar': [537]}
    actual = check(tmpdir, '/foo/537.html').line.uri.path
    assert actual == expected, repr(actual) + " isn't " + repr(expected)

def test_virtual_path_file_not_dir(tmpdir):
    pymk(tmpdir,
        ('%foo/bar.html', "Greetings from bar!")
      , ('%baz.html.spt', "Greetings from baz!")
       )
    expected = tmpdir.join('%baz.html.spt')
    actual = check(tmpdir, '/bal.html').fs
    assert actual == expected


# negotiated *and* virtual paths
# ==============================

def test_virtual_path__and_indirect_neg_file_not_dir(tmpdir):
    pymk(tmpdir,
        ('%foo/bar.html', "Greetings from bar!")
      , ('%baz.spt', "Greetings from baz!")
       )
    expected = tmpdir.join('%baz.spt')
    actual = check(tmpdir, '/bal.html')
    assert actual.fs == expected

def test_virtual_path_and_indirect_neg_noext(tmpdir):
    pymk(tmpdir, ('%foo/bar', "Greetings program!"))
    actual = check(tmpdir, '/greet/bar').fs
    expected = tmpdir.join('%foo/bar')
    assert actual == expected

def test_virtual_path_and_indirect_neg_ext(tmpdir):
    pymk(tmpdir, ('%foo/bar', "Greetings program!"))
    actual = check(tmpdir, '/greet/bar.html').fs
    expected = tmpdir.join('%foo/bar')
    assert actual == expected


# trailing slash
# ==============

def test_dispatcher_passes_through_files(tmpdir):
    pymk(tmpdir, ('foo/index.html', "Greetings, program!"))
    assert_raises_404(tmpdir, '/foo/537.html')

def test_trailing_slash_passes_dirs_with_slash_through(tmpdir):
    pymk(tmpdir, ('foo/index.html', "Greetings, program!"))
    expected = tmpdir.join('/foo/index.html')
    actual = check(tmpdir, '/foo/').fs
    assert actual == expected

def test_dispatcher_passes_through_virtual_dir_with_trailing_slash(tmpdir):
    pymk(tmpdir, ('%foo/index.html', "Greetings, program!"))
    expected = tmpdir.join('/%foo/index.html')
    actual = check(tmpdir, '/foo/').fs
    assert actual == expected

def test_dispatcher_redirects_dir_without_trailing_slash(tmpdir):
    pymk(tmpdir, 'foo')
    response = assert_raises_302(tmpdir, '/foo')
    expected = (302, '/foo/')
    actual = (response.code, response.headers['Location'])
    assert actual == expected

def test_dispatcher_redirects_virtual_dir_without_trailing_slash(tmpdir):
    pymk(tmpdir, '%foo')
    response = assert_raises_302(tmpdir, '/foo')
    expected = (302, '/foo/')
    actual = (response.code, response.headers['Location'])
    assert actual == expected

def test_trailing_on_virtual_paths_missing(tmpdir):
    pymk(tmpdir, '%foo/%bar/%baz')
    response = assert_raises_302(tmpdir, '/foo/bar/baz')
    expected = '/foo/bar/baz/'
    actual = response.headers['Location']
    assert actual == expected

def test_trailing_on_virtual_paths(tmpdir):
    pymk(tmpdir, ('%foo/%bar/%baz/index.html', "Greetings program!"))
    expected = tmpdir.join('/%foo/%bar/%baz/index.html')
    actual = check(tmpdir, '/foo/bar/baz/').fs
    assert actual == expected


# path part params
# ================

def test_path_part_with_params_works(tmpdir):
    pymk(tmpdir, ('foo/index.html', "Greetings program!"))
    expected = tmpdir.join('/foo/index.html')
    actual = check(tmpdir, '/foo;a=1/').fs
    assert actual == expected

def test_path_part_params_vpath(tmpdir):
    pymk(tmpdir, ('%bar/index.html', "Greetings program!"))
    expected = tmpdir.join('/%bar/index.html')
    actual = check(tmpdir, '/foo;a=1;b=;a=2;b=3/').fs
    assert actual == expected

def test_path_part_params_static_file(tmpdir):
    pymk(tmpdir, ('/foo/bar.html', "Greetings program!"))
    expected = tmpdir.join('/foo/bar.html')
    actual = check(tmpdir, '/foo/bar.html;a=1;b=;a=2;b=3').fs
    assert actual == expected

def test_path_part_params_simplate(tmpdir):
    pymk(tmpdir, ('/foo/bar.html.spt', "Greetings program!"))
    expected = tmpdir.join('/foo/bar.html.spt')
    actual = check(tmpdir, '/foo/bar.html;a=1;b=;a=2;b=3').fs
    assert actual == expected

def test_path_part_params_negotiated_simplate(tmpdir):
    pymk(tmpdir, ('/foo/bar.spt', "[-----]\n[-----] as text/plain\nGreetings program!"))
    expected = tmpdir.join('/foo/bar.spt')
    actual = check(tmpdir, '/foo/bar.html;a=1;b=;a=2;b=3').fs
    assert actual == expected

def test_path_part_params_greedy_simplate(tmpdir):
    pymk(tmpdir, ('/foo/%bar.spt', "[-----]\n[-----]\nGreetings program!"))
    expected = tmpdir.join('/foo/%bar.spt')
    actual = check(tmpdir, '/foo/baz/buz;a=1;b=;a=2;b=3/blam.html').fs
    assert actual == expected


# Docs
# ====

GREETINGS_NAME_SPT = "[-----]\nname = path['name']\n[------]\nGreetings, %(name)s!"

def test_virtual_path_docs_1(tmpdir):
    pymk(tmpdir, ('%name/index.html.spt', GREETINGS_NAME_SPT))
    response = handle(tmpdir, '/aspen/')
    assert response.body == "Greetings, aspen!"

def test_virtual_path_docs_2(tmpdir):
    pymk(tmpdir, ('%name/index.html.spt', GREETINGS_NAME_SPT))
    response = handle(tmpdir, '/python/')
    assert response.body == "Greetings, python!"

NAME_LIKES_CHEESE_SPT = "name = path['name'].title()\ncheese = path['cheese']\n[---------]\n%(name)s likes %(cheese)s cheese."

def test_virtual_path_docs_3(tmpdir):
    pymk(tmpdir,
        ( '%name/index.html.spt', GREETINGS_NAME_SPT),
        ( '%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT)
      )
    response = handle(tmpdir, '/chad/cheddar.txt')
    assert response.body == "Chad likes cheddar cheese."

def test_virtual_path_docs_4(tmpdir):
    pymk(tmpdir,
        ( '%name/index.html.spt', GREETINGS_NAME_SPT),
        ( '%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT)
       )
    response = handle(tmpdir, '/chad/cheddar.txt/')
    assert response.code == 404

PARTY_LIKE_YEAR_SPT = "year = path['year']\n[----------]\nTonight we're going to party like it's %(year)s!"

def test_virtual_path_docs_5(tmpdir):
    pymk(tmpdir,
        ( '%name/index.html.spt', GREETINGS_NAME_SPT),
        ( '%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT),
        ( '%year.int/index.html.spt', PARTY_LIKE_YEAR_SPT)
       )
    response = handle(tmpdir, '/1999/')
    assert response.body == "Greetings, 1999!"

def test_virtual_path_docs_6(tmpdir):
    pymk(tmpdir, ( '%year.int/index.html.spt', PARTY_LIKE_YEAR_SPT))
    response = handle(tmpdir, '/1999/')
    expected = "Tonight we're going to party like it's 1999!"
    assert response.body == expected


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

def test_virtual_path_parts_can_be_empty(tmpdir):
    pymk(tmpdir, ('foo/%bar/index.html.spt', "Greetings, program!"))
    expected = {u'bar': [u'']}
    actual = check(tmpdir, '/foo//').line.uri.path
    assert actual == expected

def test_file_matches_in_face_of_dir(tmpdir):
    pymk(tmpdir,
        ('%page/index.html.spt', 'Nothing to see here.')
      , ('%value.txt.spt', "Greetings, program!")
       )
    expected = {'value': [u'baz']}
    actual = check(tmpdir, '/baz.txt').line.uri.path
    assert actual == expected

def test_file_matches_extension(tmpdir):
    pymk(tmpdir,
        ('%value.json.spt', '[-----]\nresponse.body={"Greetings,": "program!"}')
      , ('%value.txt.spt', "[-----]\n[-----]\nGreetings, program!")
       )
    expected = "%value.json.spt"
    actual = os.path.basename(check(tmpdir, '/baz.json').fs)
    assert actual == expected

def test_file_matches_other_extension(tmpdir):
    pymk(tmpdir,
        ('%value.json.spt', '{"Greetings,": "program!"}')
      , ('%value.txt.spt', "Greetings, program!")
       )
    expected = "%value.txt.spt"
    actual = os.path.basename(check(tmpdir, '/baz.txt').fs)
    assert actual == expected

def test_virtual_file_with_no_extension_works(tmpdir):
    pymk(tmpdir, ('%value.spt', '{"Greetings,": "program!"}'))
    check(tmpdir, '/baz.txt')
    assert NoException

def test_normal_file_with_no_extension_works(tmpdir):
    pymk(tmpdir,
        ('%value.spt', '{"Greetings,": "program!"}')
      , ('value', '{"Greetings,": "program!"}')
       )
    check(tmpdir, '/baz.txt')
    assert NoException

def test_file_with_no_extension_matches(tmpdir):
    pymk(tmpdir,
        ('%value.spt', '{"Greetings,": "program!"}')
      , ('value', '{"Greetings,": "program!"}')
       )
    expected = {'value': [u'baz']}
    actual = check(tmpdir, '/baz').line.uri.path
    assert actual == expected

def test_aspen_favicon_doesnt_get_clobbered_by_virtual_path(tmpdir):
    pymk(tmpdir, '%value.spt')
    response = handle(tmpdir, '/favicon.ico')
    expected = 200
    actual = response.code
    assert actual == expected
    print(response.request.fs)

def test_robots_txt_also_shouldnt_be_redirected(tmpdir):
    pymk(tmpdir, '%value.spt')
    err = handle( tmpdir, '/robots.txt')
    actual = err.code
    assert actual == 404


