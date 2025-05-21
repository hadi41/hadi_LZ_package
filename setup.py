from setuptools import setup, find_packages
from setuptools.command.build_ext import build_ext
import subprocess
import os
# import sys # Not strictly needed in CustomBuildExt anymore
# import shutil # Not strictly needed in CustomBuildExt anymore

class CustomBuildExt(build_ext):
    def run(self):
        # Build C libraries using Make
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming Makefile is in hadi_LZ_package/hadi_LZ_package/c_backend/
        # and it builds all .dylib files directly into that c_backend directory.
        c_backend_dir = os.path.join(current_dir, 'hadi_LZ_package', 'hadi_LZ_package', 'c_backend')
        
        print(f"Running make clean and make in: {c_backend_dir}")
        
        # It's good practice to check if Makefile exists
        makefile_path = os.path.join(c_backend_dir, 'Makefile')
        if not os.path.exists(makefile_path):
            print(f"WARNING: Makefile not found at {makefile_path}. Skipping C extension build.")
            # If you want to fail the build if Makefile is missing, raise an error here.
            # super().run() # if you have other extensions defined in ext_modules
            return 

        try:
            subprocess.run(['make', 'clean', '-C', c_backend_dir], check=True)
            subprocess.run(['make', '-C', c_backend_dir], check=True) # This should build all .dylib files
        except subprocess.CalledProcessError as e:
            print(f"ERROR during make: {e}")
            raise RuntimeError("Failed to build C extensions using make.")
        except FileNotFoundError:
            print("ERROR: 'make' command not found. Please ensure make is installed and in your PATH.")
            raise RuntimeError("make command not found.")

        # No need to copy files manually here if Makefile places them correctly
        # and package_data handles their inclusion.
        
        # If you had other extensions defined via setuptools.Extension, you would call:
        # super().run()

setup(
    name="hadi_LZ_package",
    version="0.1.0", # It's good practice to have a version
    packages=find_packages(where='.', include=['hadi_LZ_package', 'hadi_LZ_package.*' ]),
    cmdclass={'build_ext': CustomBuildExt},
    install_requires=[
        'numpy>=1.19.0'
    ],
    # This tells setuptools to include these files from within the package specified.
    # The key is the package name (matching the directory name find_packages finds).
    # Here, hadi_LZ_package.hadi_LZ_package is the subpackage.
    package_data={
        'hadi_LZ_package.hadi_LZ_package': [
            'c_backend/*.so',
            'c_backend/*.dylib',
            'c_backend/*.dll'
        ],
    },
    # include_package_data=True, # Often used with MANIFEST.in, but package_data is more direct here.
    zip_safe=False # Good practice for packages with C extensions or data files not handled by standard mechanisms
)