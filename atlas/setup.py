from setuptools import find_packages, setup

tests_require = [
    "pytest-cov>=2.8,<3",
    "pytest-django>3.7.0,<4",
    "hypothesis>=5.1.5,<6",
]

dev_requires = [
    "black==19.10b0",
    "flake8>=3.7,<4",
    "flake8-quotes>=2.1.1,<3",
    "isort>=5.6.4,<6",
] + tests_require

setup(
    author="Scaife Viewer Team",
    author_email="jtauber+scaife@jtauber.com",
    description="Aligned Text and Linguistic Annotation Server (ATLAS)",
    name="scaife-viewer-atlas",
    version="0.2a1",
    url="http://github.com/scaife-viewer/backend/",
    license="MIT",
    packages=find_packages(),
    package_data={
        "atlas": []
    },
    include_package_data=True,
    test_suite="runtests.runtests",
    install_requires=[
        "django_appconf>=1.0.4",
        "django-extensions>=2.2.6,<3",
        "django-filter>=2.3.0,<3",
        "django-sortedm2m>=2.0.0,<3",
        "django-treebeard>=4.3.0,<5",
        "Django>=2.2.15,<3",
        # @@@ can be dropped in Django 3.1+
        "django-jsonfield-backport==1.0.0",
        "graphene-django==2.6.0",
        # @@@ can be dropped in Python > 3.8
        "importlib-resources>=5.1.2,<6",
        "jsonlines>=2.0.0,<3",
        "logfmt==0.4",
        "regex>=2020.11.13",
        "tqdm>= 4.48.2,<5",
    ],
    tests_require=tests_require,
    extras_require={
        "test": tests_require,
        "dev": dev_requires,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    zip_safe=False
)


