from distutils.core import setup

setup(
    name='django-pyfixtures',
    version='0.1',
    author='Chase Seibert',
    author_email='chase.seibert@gmail.com',
    packages=['pyfixtures'],
    url='https://github.com/chase-seibert/pyfixtures',
    license='LICENSE.txt',
    description='dumpdata generates python source code files as the fixtures',
    long_description=open('README.md').read(),
)
