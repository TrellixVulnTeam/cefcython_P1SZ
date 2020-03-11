from distutils.core import Command
from distutils.command.build import build
from setuptools import setup, find_packages
from setuptools.extension import Extension

from Cython.Build import cythonize

import cefcython
import os
import subprocess
import tarfile

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
DEBUG = os.environ.get('CEF_DEBUG', False)

extensions = [
    Extension(
        'cefcython.capi.*',
        ['cefcython/capi/*.pyx'],
        include_dirs=cefcython.get_include_dirs(),
    ),
    Extension(
        'cefcython.util.*',
        ['cefcython/util/*.pyx'],
        include_dirs=cefcython.get_include_dirs(),
    ),
]

package_data={
    'cefcython.capi': ['*.pxd'],
    'cefcython.util': ['*.pxd'],
    'cefcython.build': [
        'include/*.h',
        'include/capi/*.h',
        'include/internal/*.h',
        'include/base/*.h',
        'include/base/internal/*.h',
    ],
}

class ExtractCEFCommand(Command):
    description = 'extract CEF from binary distribution'

    def initialize_options(self):
        self.build_lib = None
        self.build_temp = None
        self.cef_dist = os.environ.get('CEF_DIST', '')
        self.cef_dist_name = None

    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_lib', 'build_lib'),
                                   ('build_temp', 'build_temp'))

        assert os.path.exists(self.cef_dist), 'CEF dist {} does not exist'.format(self.cef_dist)

        self.cef_dist_name = os.path.basename(self.cef_dist).split('.tar')[0]

    def run(self):
        with tarfile.open(self.cef_dist, 'r') as tf:
            tf.extractall(path=self.build_temp)

class InstallCEFCommand(Command):
    description = 'install CEF from extracted distribution'

    def initialize_options(self):
        self.build_lib = None
        self.build_temp = None
        self.cef_dist_name = None
        self.include_dirs = None

    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_lib', 'build_lib'),
                                   ('build_temp', 'build_temp'))
        self.set_undefined_options('extract_cef',
                                   ('cef_dist_name', 'cef_dist_name'))

    def install(self):
        global DEBUG
        cef_path = os.path.join(self.build_temp, self.cef_dist_name)
        for install_dir, dest in [('Release' if not DEBUG else 'Debug', '.'), ('Resources', '.')]:
            self.copy_tree(
                os.path.join(os.path.join(cef_path, install_dir)),
                os.path.join(self.build_lib, os.path.join(os.path.join('cefcython', 'cef'), dest))
            )

    def run(self):
        self.install()

class StripCEFBinariesCommand(Command):
    description = 'strip installed binaries'

    def initialize_options(self):
        self.build_temp = None
        self.cef_dist_name = None

    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_temp', 'build_temp'))
        self.set_undefined_options('extract_cef',
                                   ('cef_dist_name', 'cef_dist_name'))

    def run(self):
        cef_path = os.path.join(self.build_temp, self.cef_dist_name)
        for dirpath, dirnames, filenames in os.walk(cef_path):
            for filename in filenames:
                try:
                    cmd = ['strip', os.path.join(dirpath, filename)]
                    subprocess.check_call(cmd, stderr=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    pass
                else:
                    self.announce('Stripped {}'.format(filename), level=2)


class BuildCommand(build):
    def run(self):
        self.run_command('extract_cef')
        if not DEBUG:
            self.run_command('strip_cef_binaries')
        self.run_command('install_cef')
        build.run(self)

from cefcython import __version__ as version

setup(
    name='cefcython',
    version=version,
    author='Joseph Kogut',
    author_email='joseph.kogut@gmail.com',
    description='Cython bindings for CEF',
    install_requires=['cython'],
    packages=find_packages(),
    package_data=package_data,
    ext_modules=cythonize(extensions, gdb_debug=DEBUG),
    zip_safe=False,
    cmdclass={
        'build': BuildCommand,
        'extract_cef': ExtractCEFCommand,
        'install_cef': InstallCEFCommand,
        'strip_cef_binaries': StripCEFBinariesCommand,
    }
)
