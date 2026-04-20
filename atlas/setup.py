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
    version="0.3rc4",
    url="http://github.com/scaife-viewer/backend/",
    license="MIT",
    packages=find_packages(),
    package_data={
        "atlas": []
    },
    include_package_data=True,
    test_suite="runtests.runtests",
    install_requires=[
        "django_appconf>=1.0.6",
        "django-extensions==3.2.3",
        "django-filter>=21.1,<24.1",
        "django-sortedm2m>=3.0.0,<4.0.0",
        "django-treebeard>=4.7.1,<5",
        "Django>=3.1,<4",
        "graphene-django==3.2.2",
        "PyYAML==6.0.2",
        "jsonlines>=2.0.0,<3",
        "regex>=2020.11.13",
        "tqdm>= 4.48.2,<5",
        # FIXME: Make an extras package
        # "PyICU>=2.9,<3"
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
