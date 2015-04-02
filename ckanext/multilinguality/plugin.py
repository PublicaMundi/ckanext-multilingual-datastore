from logging import getLogger

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckan.common import request
from routes.mapper import SubMapper
import ckan.model as model

import ckanext.multilinguality.logic.action as action
import ckanext.multilinguality.logic.auth as auth
import ckanext.multilinguality.controllers.package as package_controller

import pprint
import json
log = getLogger(__name__)


class ReclinePreviewMultilinguality(p.SingletonPlugin):
    """This extension previews resources using recline

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IResourcePreview`` allows to add previews
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IAuthFunctions)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''
        toolkit.add_public_directory(config, 'theme/public')
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_resource('theme/public', 'ckanext-multilinguality')

    def get_helpers(self):
        return {
                #'resource_edit': resource_edit,
                'get_translations': self.get_translations,
                }

    def can_preview(self, data_dict):
        # if the resource is in the datastore then we can preview it with recline
        if data_dict['resource'].get('datastore_active'):
            return True
        format_lower = data_dict['resource']['format'].lower()
        return format_lower in ['csv', 'xls', 'tsv']

    def preview_template(self, context, data_dict):
        return 'recline_read.html'

    def before_map(self, mapper):
        mapper.connect(
                'resource_translate',
                '/dataset/{id}/resource_translate/{resource_id}',
                controller='ckanext.multilinguality.controllers.package:UserController',
                action = 'resource_translate')

        mapper.connect(
                '/dataset/{id}/resource_translate_inner/{resource_id}',
                controller='ckanext.multilinguality.controllers.package:UserController',
                action = 'resource_datapreview')

        #mapper.connect('/translate/dump/{resource_id}/{language}',
        #          controller='ckanext.multilinguality.controller:DatastoreController',
        #          action='dump')

        return mapper

    def before_view(self, data_dict):
        print 'BEFORE VIEW'
        #language = request.environ['CKAN_LANG']
        #pprint.pprint(data_dict)
        #resources = data_dict.get('resources')
        #t = resources[0]
        #resources[0] = resources[1]
        #resources[1] = t
        #data_dict.update({'resources':resources})
        return data_dict

    def after_update(self, context, data_dict):
        print 'AFTERT UPDATE'
        return data_dict

    def after_delete(self, context, data_dict):
        print 'AFTER DELETE'

    def after_show(self, context, data_dict):
        # TODO: Need to cut extra translation resources here
        # so they are not visible in UI/other API functions

        #for k,v in data_dict.iteritems():
        #    if k=='resources':
        #        new_res = []
        #        for res in v:
        #            if not 'translation_resource' in res:
        #                new_res.append(res)
        #        data_dict.update({k:new_res})
        #data_dict.update({'num_resources':len(new_res)})
        #print 'NEW DICT'
        #pprint.pprint(data_dict.get('resources'))
        #language = request.environ['CKAN_LANG']
        #data_dict = {}
        #context = {}
        # TODO: Can i replace resource here with 
        #res = context.get('resource')
        #print 'res'
        #del context['resource']
        #pprint.pprint(res)
        #res2 = p.toolkit.get_action('resource_show')(context, {'id':json.loads(res.extras.get('has_translations')).get('en')})
        #print 'res2'
        #pprint.pprint(res2)
        return data_dict

    def get_actions(self):
        return {
                'translate_resource_create': action.translate_resource_create,
                'translate_resource_update': action.translate_resource_update,
                'translate_resource_search': action.translate_resource_search,
                'translate_resource_delete': action.translate_resource_delete,
                'translate_resource_publish': action.translate_resource_publish,
                }

    def get_translations(self, res):
        orig_lang = res.get('resource_language', None)
        print 'translation'
        print (orig_lang)
        if not orig_lang:
            return None
        #return 
        #json.loads(res.get('has_translations','u{'+orig_lang+'}'))
        translations = json.loads(res.get('has_translations', u'{}'))
        context = {
                'model':model,
                'session':model.Session,
                'ignore_auth':True,
                'api_version':3,
                }
        published_langs = [orig_lang]
        for lang,id in translations.iteritems():
            trans_res = toolkit.get_action('resource_show')(context, {'id':id})
            print 'trans res'
            print trans_res
            if trans_res.get('translation_status') == 'published':
                published_langs.append(lang)
        return published_langs


    def get_auth_functions(self):
        return {
                'translate_resource_create': auth.translate_resource_create,
                'translate_resource_update': auth.translate_resource_update,
                'translate_resource_search': auth.translate_resource_search,
                'translate_resource_delete': auth.translate_resource_delete,
                'translate_resource_publish': auth.translate_resource_publish,
                }
