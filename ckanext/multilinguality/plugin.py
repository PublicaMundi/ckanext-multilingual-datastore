from logging import getLogger

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckan.common import request
from routes.mapper import SubMapper
import ckan.model as model

import ckanext.multilinguality.logic.action as action
import ckanext.multilinguality.logic.auth as auth
import ckanext.multilinguality.controllers.package as package_controller
import ckan.lib.i18n as i18n

import pprint
import json
log = getLogger(__name__)


class ReclinePreviewMultilinguality(p.SingletonPlugin):
    """This extension previews resources using recline

        This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IResourcePreview`` allows to add previews

        Important note: For the moment since there is not way to select better preview, if recline preview is enabled recline-multilingual plugin
                        must be loaded with higher priority in development.ini
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IAuthFunctions)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IResourceController)

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
                'get_resource_languages': self.get_resource_languages,
                'get_orig_language': self.get_orig_language,
                #'get_translation_resource': self.get_translation_resource,
                'get_language_translation_status': self.get_language_translation_status
                }

    def can_preview(self, data_dict):
        # if the resource is in the datastore then we can preview it with recline
        #return True
        if data_dict['resource'].get('datastore_active'):
            return True
        format_lower = data_dict['resource']['format'].lower()
        previewable = format_lower in ['csv', 'xls', 'tsv']
        return {
                'can_preview': previewable,
                'quality': 3
                }

    def preview_template(self, context, data_dict):
        return 'recline_read_translated.html'

    def before_map(self, mapper):
        mapper.connect(
                'resource_translate',
                '/dataset/{id}/resource_translate/{resource_id}/language/{language}',
                controller='ckanext.multilinguality.controllers.package:UserController',
                action = 'resource_translate')

        mapper.connect(
                '/dataset/{id}/resource_translate_inner/{resource_id}/{language}',
                controller='ckanext.multilinguality.controllers.package:UserController',
                action = 'resource_datapreview')

        #mapper.connect('/translate/dump/{resource_id}/{language}',
        #          controller='ckanext.multilinguality.controller:DatastoreController',
        #          action='dump')

        return mapper

    def after_update(self, context, data_dict):
        # TODO: wrong data_dict output
        # doesnt contain resources
        return data_dict
        new_res_list = []
        for res in data_dict.get('resources'):
            if res.get('translation_resource'):
                found = False
                for nres in data_dict.get('resources'):
                    if nres.get('id') == res.get('translation_parent_id') and not nres.get('state') == 'deleted':
                        found = True
                        new_res_list.append(res)
                        break
            else:
                new_res_list.append(res)
            break
        data_dict.update({'resources': new_res_list})

        return data_dict
        '''
        print 'AFTERT UPDATE'
        for k,v in data_dict.iteritems():
            if k=='resources':
                new_res = []
                for res in v:
                    print 'res='
                    print res
                    if not res.get('resource_language'):
                        print 'NO RES LANG'
                        #self.set_orig_language(res, data_dict)
                        #res.update({'resource_language': 'en'})
                        print res.get('resource_language')
        #            if not (('translation_resource' in res) and res.get('translation_status')=='published'):
        #                new_res.append(res)
        #        data_dict.update({k:new_res})
        print 'ALL RESOURCES'
        pprint.pprint(data_dict['resources'])
        return data_dict
        '''
    def before_show(self, resource_dict):
        return resource_dict
    #def after_update(self, context, data_dict):
    #    print 'BEFORE UPDATE'
    #    resources = data_dict.get('resources')
    #    new_resources = copy.deepcopy(resources)
    #    for res in resources:
    #        translations = json.loads(res.get('has_translations', u'{}'))
    #        for trans,id in translations.iteritems():
    #            res = p.toolkit.get_action('resource_show')(context, {'id':id})
    #            new_resources.append(res)
    #    data_dict.update({'resources':new_resources, 'num_resources':len(new_resources)})

    def after_delete(self, context, data_dict):
        print 'AFTER DELETE'
        #return data_dict

    def after_show(self, context, data_dict):
        return data_dict
        #print context
         
        user_orgs = p.toolkit.get_action('organization_list_for_user')(context, {'id':context.get('user')})
        org_user = False
        if data_dict.get('owner_org') in [u.get('id') for u in user_orgs]:
            org_user = True
            # Package belongs to user organization
            # in case there are unpublished translation resources
            # keep them in the API
            # otherwise hide completely
        for k,v in data_dict.iteritems():
            if k=='resources':
                new_res = []
                for res in v:
                    if ('translation_resource' in res):
                        if org_user:
                            #and not res.get('translation_status') == 'published':
                            new_res.append(res)
                    else:
                        new_res.append(res)
                        #and res.get('translation_status')=='published'):
                        #new_res.append(res)
                data_dict.update({k:new_res})
        data_dict.update({'num_resources':len(new_res)})
        
        return data_dict

    def before_view(self, data_dict):
        # TODO: Need to cut extra translation resources here
        # so they are not visible in UI/other API functions
        #return data_dict
        return data_dict
        '''
        for k,v in data_dict.iteritems():
            if k=='resources':
                new_res = []
                for res in v:
                    if not 'translation_resource' in res:
                        new_res.append(res)
                data_dict.update({k:new_res})
        data_dict.update({'num_resources':len(new_res)})
        
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
        '''
    def get_actions(self):
        return {
                'translate_resource_create': action.translate_resource_create,
                'translate_resource_update': action.translate_resource_update,
                'translate_resource_search': action.translate_resource_search,
                'translate_resource_delete': action.translate_resource_delete,
                'translate_resource_publish': action.translate_resource_publish,
                'translate_resource_unpublish': action.translate_resource_unpublish,
                }

    def _get_context(self):
        return {
                'model':model,
                'session':model.Session,
                #'user': model.User,
                'ignore_auth':False,
                'api_version':3,
                }

    def get_language_translation_status(self, res, lang):
        orig_lang = self.get_orig_language(res)
        translations = json.loads(res.get('has_translations', '{}'))
        lang = unicode(lang)
        if lang not in translations.keys():
            return 'none'
        context = self._get_context()
        trans_id = translations[lang]
        trans_res = toolkit.get_action('resource_show')(context, {'id':trans_id})
        return trans_res.get('translation_status')

    def get_resource_languages(self, res):
        orig_lang = self.get_orig_language(res)
        if not orig_lang:
            return None
        #return 
        #json.loads(res.get('has_translations','u{'+orig_lang+'}'))
        translations = json.loads(res.get('has_translations', '{}'))
        context = self._get_context()
        published_langs = [orig_lang]
        for lang,id in translations.iteritems():
            trans_res = toolkit.get_action('resource_show')(context, {'id':id})
            if trans_res.get('translation_status') == 'published':
                published_langs.append(lang)
        return published_langs

    def _decide_language(self, res):
        # Have to decide original resource language
        #if 'inspire' in pkg:
        #    for lang_code in pkg.get('inspire').resource_language:
        #        print 'found!'
        #        print lang_code[:-1]
                #return lang_code
        return 'en'

    def get_orig_language(self, res):
        available_locales = i18n.get_available_locales()

        res_lang = self._decide_language(res)
        orig_lang = res.get('language', res_lang)
        for locale in available_locales:
            if locale == orig_lang:
                return locale
 
    def get_auth_functions(self):
        return {
                'translate_resource_create': auth.translate_resource_create,
                'translate_resource_update': auth.translate_resource_update,
                'translate_resource_search': auth.translate_resource_search,
                'translate_resource_delete': auth.translate_resource_delete,
                'translate_resource_publish': auth.translate_resource_publish,
                }
