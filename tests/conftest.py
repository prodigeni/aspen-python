"""
This is in the default search path for pytest fixtures, so we might as
well also put Aspen-dev-specific helpers used in multiple tests here.
"""

def pymk(localdir, *treedef):
    """Easily make a tree under localdir, presuming it's a py.path;
       syntax-similar to old aspen 'mk' helper.
    """
    results = []
    for item in treedef:
        if isinstance(item, basestring):
            results.append(localdir.join(item.lstrip('/')))
            results[-1].ensure(dir=True)
        elif isinstance(item, tuple):
            filepath, contents = item
            results.append(localdir.ensure(filepath))
            results[-1].write(contents)
    return results

