from setuptools import setup, find_packages

exclude_dirs = ['ez_setup', 'examples', 'tests', 'venv']

# Runtime requirements
reqs = [
    'requests',
    'six',
    'future',
    'aenum'
]

# Requirements for testing
test_reqs = ['pytest', 'hypothesis', 'requests_mock']

# Requirements for setup
setup_reqs = ['flake8', 'pep8', 'pytest-runner']

setup(
    name='fabricate-it',
    version='1.0.1',
    author='Brett Levenson',
    author_email='blevenson@apple.com',
    description='A library that makes creating API clients simple and declarative',
    url='https://github.com/boichee/fabricator',
    packages=find_packages(exclude=exclude_dirs),
    install_requires=reqs,
    tests_require=test_reqs,
    setup_requires=setup_reqs,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Topic :: Software Development',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers'
    ]
)