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
    "isort>=4.3.21,<5",
] + tests_require

setup(
    author="Scaife Viewer Team",
    author_email="jtauber+scaife@jtauber.com",
    description="Scaife Viewer Backend :: Core Functionality",
    name="scaife-viewer-core",
    version="0.1a9",
    url="https://github.com/scaife-viewer/backend/",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    test_suite="runtests.runtests",
    install_requires=[
        "anytree==2.4.3",
        "certifi==2018.11.29",
        "dask[bag]==1.1.0",
        "django_appconf>=1.0.4",
        "Django>=2.2,<3.0",
        "elasticsearch>=7.0.0,<8.0.0",
        "google-auth==1.6.2",
        "google-cloud-pubsub==0.39.1",
        "lxml>=4.3.5",
        "MyCapytain==3.0.1",
        "python-dateutil==2.7.5",
        "python-mimeparse==1.6.0",
        "rdflib==4.2.2",
        "regex>=2020.11.13",
        "requests==2.22.0",
        "wrapt==1.11.1",
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

