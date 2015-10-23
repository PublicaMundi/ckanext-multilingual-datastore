from ckan.lib.base import (
    c, request, response, render, abort, redirect, BaseController)
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.lib.datapreview as datapreview
import json

NotFound = toolkit.ObjectNotFound
NotAuthorized = toolkit.NotAuthorized

class UserController(BaseController):
    def resource_translate(self, resource_id, id, language):
        #self._change_trans_res_status(resource_id, language)
        pkg_dict = self._check_pkg_access(id)
        res = self._check_res_access(resource_id)
        self._check_trans_res_status(res, language)

        self._setup_template_variables(pkg_dict, res, language)

        return render('package/resource_translate.html')

    def resource_datapreview(self, resource_id, id, language):
        '''
        Embeded page for a resource data-preview.

        Depending on the type, different previews are loaded.  This could be an
        img tag where the image is loaded directly or an iframe that embeds a
        webpage, recline or a pdf preview.
        '''
        print 'OOOO'
        print resource_id
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user or c.author,
            'auth_user_obj': c.userobj
        }

        try:
            c.resource = toolkit.get_action('resource_show')(context,
                                                     {'id': resource_id})
            c.package = toolkit.get_action('package_show')(context, {'id': id})
            c.resource_language = language

            data_dict = {'resource': c.resource, 'package': c.package}

            preview_plugin = datapreview.get_preview_plugin(data_dict)

            if preview_plugin is None:
                abort(409, _('No preview has been defined.'))

            #preview_plugin.setup_template_variables(context, data_dict)
            c.resource_json = json.dumps(c.resource)
        except NotFound:
            abort(404, _('Resource not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read resource %s') % id)
        else:
            #return render(preview_plugin.preview_template(context, data_dict))
            return render('recline_translate_edit.html')

    #def edit_page(self):
    def _check_pkg_access(self, name_or_id):
        context = self._get_context()
        try:
            pkg_dict = toolkit.get_action('package_show')(context, {'id':name_or_id})
            return pkg_dict
        except NotFound:
            abort(404, _('Package not found'))
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

    def _check_res_access(self, resource_id):
        context = self._get_context()
        try:
            pkg_dict = toolkit.get_action('resource_show')(context, {'id':resource_id})
            print 'RESOURCE='
            print pkg_dict
            return pkg_dict
        except NotFound:
            abort(404, _('Resource not found'))
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

    def _check_trans_res_status(self, res, language):
        context = self._get_context()
        print 'before trans get'
        trans_res = self._get_translation_resource(res, language)
        print 'TRAN RES'
        print trans_res
        if not trans_res:
            return
        if trans_res.get('translation_status') == 'published':
            data = {'resource_id':res.get('id'), 'language':language }
            print 'attempting unpublish'
            return toolkit.get_action('translate_resource_unpublish')(context, data)
            print 'unpublished'
        #trans_res = self._get_translation_resource(resource_id, language)
        #print 'TRAN RES after'
        #print trans_res

    def _get_translation_resource(self, res, language):
        context = self._get_context()
        available_translations = json.loads(res.get('has_translations','{}'))
        if not available_translations.get(language):
            return None
        data = {'id':available_translations.get(language)}
        return toolkit.get_action('resource_show')(context, data)

    def _get_context(self):
        context = {
            #'for_view': True,
            'user': c.user or c.author,
            'auth_user_obj': c.userobj
        }
        return context

    def _setup_template_variables(self, pkg_dict, resource, language):
        #c.is_sysadmin = False # Fixme: why? normally should be computed
        #c.user_dict = user_dict
        #c.is_myself = user_dict['name'] == c.user
        #c.about_formatted = h.render_markdown(user_dict['about'])
        #c.pkg_dict = pkg_dict
        c.package = pkg_dict
        c.resource = resource
        c.resource_language = language

