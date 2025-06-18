
import os

from setuptools import setup, find_packages

def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}

setup(
    name="corfogeneratecode",
    version="2.0.0",
    author="Oficina EOL UChile",
    author_email="eol-ing@uchile.cl",
    description="Allows you to generate corfo code",
    url="https://eol.uchile.cl",
    packages=find_packages(),
    install_requires=[
        'XBlock',
        ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'xblock.v1': ['corfogeneratecode = corfogeneratecode:CorfoGenerateXBlock'],
        "lms.djangoapp": ["corfogeneratecode = corfogeneratecode.apps:CorfoGenerateConfig"],
        "cms.djangoapp": ["corfogeneratecode = corfogeneratecode.apps:CorfoGenerateConfig"]
    },
    package_data=package_data("corfogeneratecode", ["static", "public"]),
)
