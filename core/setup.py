from setuptools import find_packages, setup

tests_require = [
    "pytest-cov>=2.8,<3",
    "pytest-django>3.7.0,<4",
    "hypothesis>=5.1.5,<6",
]

dev_requires = [
    "flake8==3.6.0",
    "flake8-quotes==1.0.0",
    "isort==4.3.4",
] + tests_require

setup(
    author="Scaife Viewer Team",
    author_email="jtauber+scaife@jtauber.com",
    description="Scaife Viewer Backend :: Core Functionality",
    name="scaife-viewer-core",
    version="0.1-a1",
    url="https://github.com/scaife-viewer/backend/",
    license="MIT",
    packages=find_packages(),
    package_data={
        "core": []
    },
    test_suite="runtests.runtests",
    install_requires=[
        "anytree==2.4.3",
        "certifi==2018.11.29",
        "dask[bag]==1.1.0",
        "Django==2.1.11",
        "elasticsearch==6.3.1",
        "google-auth==1.6.2",
        "google-cloud-pubsub==0.39.1",
        "lxml==4.3.0",
        "MyCapytain==2.0.9",
        "python-dateutil==2.7.5",
        "python-mimeparse==1.6.0",
        "rdflib==4.2.2",
        "regex==2018.11.22",
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

