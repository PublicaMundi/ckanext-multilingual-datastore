from setuptools import setup, find_packages

version = '0.1'

setup(
    name='ckanext-multilingual_datastore',
    version=version,
    description="A CKAN extension that provides UI tools and API calls for translating and viewing tabular resources",
    long_description="""\
    """,
    classifiers=[],
    keywords='ckan, multilinguality, datastore, preview',
    author='Stelios Manousopoulos',
    author_email='smanousopoulos@imis.athena-innovation.gr',
    url='https://github.com/PublicaMundi/ckanext-multilingual_datastore',
    license='GPLv3',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.multilingual_datastore'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
    ],
    entry_points=\
    """
    [ckan.plugins]
    multilingual_datastore=ckanext.multilingual_datastore.plugin:MultilingualDatastore
    """,
)
