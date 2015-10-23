'''
These exported vocabularies are intended to be read-only instances of zope
SimpleVocabulary. In most cases, there will be no need to access directly 
(but via the read-only API or via Thesaurus properties).
'''

trans_vocabularies = {}

# Import loader

from ckanext.multilinguality.json_loader import (
    make_vocabularies, normalize_keyword, normalize_thesaurus_title)

def _update(data_file, name_prefix='', overwrite=False):
    '''Update the module-global vocabularies from external JSON data.
    '''
    for name, desc in make_vocabularies(data_file):
        #assert overwrite or not (name in trans_vocabularies), (
        #    'A vocabulary named %r is already loaded' % (name))
        trans_vocabularies[name_prefix + name] = desc

# Utilities

def get_titles():
    return { k: trans_vocabularies[k]['title'] for k in trans_vocabularies }
from ckanext.publicamundi import reference_data

_update(
    reference_data.get_path('inspire-vocabularies.json'), 
    name_prefix='')

def get_names():
    return trans_vocabularies.keys()

def get_by_title(title):
    keys = filter(lambda t: trans_vocabularies[t]['title'] == title, trans_vocabularies.keys())
    if keys:
        k = keys[0]
        return trans_vocabularies[k]
    else:
        return None

def get_by_name(name):
    return trans_vocabularies.get(name)

# Initialize - Load common vocabularies

from ckanext.multilinguality import reference_data

_update(
    reference_data.get_path('inspire-vocabularies.json'), 
    name_prefix='')

