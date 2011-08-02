from setuptools import setup
import sys
import os

wd = os.path.dirname(os.path.abspath(__file__))
os.chdir(wd)
sys.path.insert(1, wd)

name = 'MusixFlask'
pkg = __import__(name)
author, email = pkg.__author__.rsplit(' ', 1)

with open(os.path.join(wd, 'README.rst'),'r') as readme:
    long_description = readme.read()

python_version = sys.version_info[:2]
url = 'http://projects.monkeython.com/musixmatch/%s' % name

application = {
    'name': name,
    'version': pkg.__version__,
    'author': author,
    'author_email': email.strip('<>'),
    'url': '%s/html' % url,
    'description': "Flask application to browse Musixmatch database.",
    'long_description': long_description,
    'download_url': '%s/eggs/%s-%s-py%s.%s.egg' % \
        ((url, name, version) + python_version),
    'classifiers': pkg.__classifiers__,
    'py_modules': [name],
    'requires': ['musixmatch', 'Flask'],
    'include_package_data': True,
    'exclude_package_data': {name: ["*.rst", "docs", "tests"]},
    'test_suite': 'tests.suite' }

setup(application)

