import logging

import pylons
import sqlalchemy
import json
import pprint

from unidecode import unidecode
import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as p
import ckanext.multilinguality.db as db
import ckanext.multilinguality.logic.schema as dsschema

import uuid
#from ckan.lib.celery_app import celery

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust
_validate = ckan.lib.navl.dictization_functions.validate


def translate_resource_create(context, data_dict):
    '''Creates a new resource and creates a datastore table associated to
    the original resource whose id is provided

    '''
    p.toolkit.check_access('translate_resource_create', context, data_dict)

    schema = context.get('schema', dsschema.translate_resource_create_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    #package = p.toolkit.get_action('dataset_show')(context, {'id': data_dict.get('package_id')})
    res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    #try:
    # Check if datastore table exists
    ds = p.toolkit.get_action('datastore_search')(context, {'resource_id': data_dict.get('resource_id')})
    #except p.toolkit.ObjectNotFound:
    #    log.info('Resource {0} does not have a datastore table associated with it'.format(data_dict.get('id')))
    #    return
    try:
        has_translations = json.loads(res.get('has_translations'))
    except:
        has_translations = {}
    if data_dict.get('language') in has_translations.keys():
        log.info('Resource {0} in language {1} already exists'.format(data_dict.get('id'), data_dict.get('language')))
        raise p.toolkit.ValidationError('Translation resource in language {0} already exists'.format(data_dict.get('language')))

    ### TODO: resource_show doesnt display package_id until CKAN 2.3
    # Now demanding package_id parameter
    # In case resource doesnt provide a name, use id instead

    # Create resource if it doesnt exist with proper metadata
    if res.get('name') is not None:
        new_res_name = res.get('name') + ' ('+data_dict.get('language')+')'
    else:
        new_res_name = res.get('id') + ' ('+data_dict.get('language')+')'

    fields = ds.get('fields')
    columns = {}
    for field in fields:
        col = {field.get('id')}
        if field.get('type') != 'text':
            columns.update({field.get('id'):'no-translate'})
        else:
            columns.update({field.get('id'):''})

    columns = json.dumps(columns)

    new_res = p.toolkit.get_action('resource_create')(context,
            {
                'package_id': data_dict.get('package_id'),
                'url':'http://',
                'format':'data_table',
                'name': new_res_name,
                'description': 'This is a resource created for translation purposes',
                'translation_parent_id': data_dict.get('resource_id'),
                'translation_resource': True,
                'translation_language': data_dict.get('language'),
                'translation_status': 'draft',
                'state': 'active',
                'translation_columns':columns,
            })

    # Update original resource metadata
    has_translations.update({data_dict.get('language'):new_res.get('id')})
    res = p.toolkit.get_action('resource_update')(context,
            {
                'id':res.get('id'),
                'has_translations': json.dumps(has_translations),
                'format': res.get('format'),
                'url': res.get('url')
                }
            )

    # Initialize empty datastore table associated to resource
    new_ds = p.toolkit.get_action('datastore_create')(context,
            {
                'resource_id': new_res.get('id'),
                'force':True,
            })

    return new_res

def translate_resource_update(context, data_dict):
    '''Update or insert column given the (translation) resource_id, column_name
    and translation method(manual, automatic, transcription

    '''
    p.toolkit.check_access('translate_resource_update', context, data_dict)

    schema = context.get('schema', dsschema.translate_resource_update_schema())

    #records = data_dict.pop('records', None)
    data_dict, errors = _validate(data_dict, schema, context)
    #if records:
    #    data_dict['records'] = records
    if errors:
        raise p.toolkit.ValidationError(errors)

    res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    # Check if candidate resource is translation resource
    if not res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is not a translation resource'.format(res.get('id')))

    original_res = p.toolkit.get_action('resource_show')(context, {'id': res.get('translation_parent_id')})

    ds = p.toolkit.get_action('datastore_search')(context, {'resource_id': data_dict.get('resource_id')})
    original_ds = p.toolkit.get_action('datastore_search')(context, {'resource_id': res.get('translation_parent_id')})

    # Check if column_name exists in original table
    col_name = data_dict.get('column_name')
    field_exists = False
    for field in original_ds.get('fields'):
        if field['id'] == col_name:
            field_exists = True
            break
    if not field_exists:
        raise p.toolkit.ValidationError('Column name "{0}" does not correspond to any "{1}" table columns'.format(data_dict.get('column_name'),res.get('translation_parent_id')))

    _initialize_column(context, col_name, ds, original_ds.get('total'))

    mode = data_dict.get('mode')
    if mode == 'manual':
        return _translate_manual(context, res, col_name, original_ds, ds)
    elif mode == 'automatic':
        return _translate_automatic(context, res, ds)
    elif mode == 'transcription':
        _transcript(context, res, col_name, original_ds, ds)
    else:
        log.info('Should never reach here')
        return

    return

def translate_resource_delete(context, data_dict):
    '''Delete a column or the whole resource given a (translation) resource_id and/or column_name

    '''
    p.toolkit.check_access('translate_resource_delete', context, data_dict)

    schema = context.get('schema', dsschema.translate_resource_delete_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    if not res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is not a translation resource'.format(res.get('id')))

    original_res = p.toolkit.get_action('resource_show')(context, {'id': res.get('translation_parent_id')})

    # Delete column if option is set
    # TODO: datastore doesnt support deleting a whole column - dont support this
    filters = {}
    if 'column_name' in data_dict:
        #filters = {data_dict.get('column_name'):'*'}
        # Delete datastore table
        print 'Delete only column!'

        ds = p.toolkit.get_action('datastore_search')(context, {'id':data_dict.get('resource_id')})
        #total = ds.get('total')
        # Check if column_name exists in original table
        col_name = data_dict.get('column_name')
        field_exists = False
        for field in ds.get('fields'):
            if field['id'] == col_name:
                field_exists = True
                break
        if not field_exists:
            raise p.toolkit.ValidationError('Column name "{0}" does not correspond to any "{1}" table columns'.format(col_name, ds.get('resource_id')))

        columns = json.loads(res.get('translation_columns'))
        for k,v in columns.iteritems():
            if k == col_name:
                columns.update({k:'manual'})

        columns = json.dumps(columns)
        res = p.toolkit.get_action('resource_update')(context, {
                'id': res.get('id'),
                'url': res.get('url'),
                'format': res.get('format'),
                'translation_parent_id': res.get('translation_parent_id'),
                'translation_resource': True,
                'translation_language': res.get('translation_language'),
                'translation_status': res.get('translation_status'),
                'translation_columns':columns,
                })

        filters = {col_name:'*'}
        #la = _delete_column(context, data_dict.get('column_name'), ds, total)
        #return
        print 'after initialize'
        print col_name
        #pprint.pprint(la)
        #filters = {}
        return p.toolkit.get_action('datastore_delete')(context, {'resource_id': data_dict.get('resource_id'), 'filters':filters, 'force':True})

    # Delete datastore table
    try:
        p.toolkit.get_action('datastore_delete')(context, {'resource_id': data_dict.get('resource_id'), 'filters':filters, 'force':True})
    except:
        return

    # Update metadata and delete resouce
    try:
        has_translations = json.loads(original_res.get('has_translations'))
    except p.toolkit.ValidationError:
        log.info('Original resource has no translation metadata. Something went wrong...')

    del has_translations[res.get('translation_language')]

    upd_original_res = p.toolkit.get_action('resource_update')(context, {
        'id':original_res.get('id'),
        'url_type': original_res.get('url_type'),
        'url':original_res.get('url'),
        'format':original_res.get('format'),
        'has_translations':json.dumps(has_translations)
        })
    return p.toolkit.get_action('resource_delete')(context, {'id': data_dict.get('resource_id')})

def translate_resource_publish(context, data_dict):
    '''Publishes the translation resource
    by changing its state and perhaps creating a view associated with it?
    '''
    p.toolkit.check_access('translate_resource_publish', context, data_dict)

    schema = context.get('schema', dsschema.translate_resource_publish_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    #package = p.toolkit.get_action('dataset_show')(context, {'id': data_dict.get('package_id')})
    res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    if not res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is not a translation resource'.format(res.get('id')))

    # Update resource metadata
    p.toolkit.get_action('resource_update')(context, {
        'id':res.get('id'),
        'url':res.get('url'),
        'format':res.get('format'),
        'translation_parent_id': res.get('translation_parent_id'),
        'translation_resource': True,
        'translation_language': res.get('translation_language'),
        'translation_status': 'published',
        })
    return
    # Create view? 

def translate_resource_search(context, data_dict):
    '''Search translation resources given resource_id, and filters?
    and translation method(manual, automatic, transcription

    '''
    # TODO : check access not working correctly, doesnt allow access via api, why??
    #p.toolkit.check_access('translate_resource_search', context, data_dict)

    schema = context.get('schema', dsschema.translate_resource_search_schema())

    #records = data_dict.pop('records', None)
    data_dict, errors = _validate(data_dict, schema, context)
    #if records:
    #    data_dict['records'] = records
    if errors:
        raise p.toolkit.ValidationError(errors)

    res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    try:
        has_translations = json.loads(res.get('has_translations'))
    except:
        has_translations = {}
    if not data_dict.get('language') in has_translations.keys():
        raise p.toolkit.ValidationError('Translation resource in language {0} does not exist'.format(data_dict.get('language')))
    trans_res = p.toolkit.get_action('resource_show')(context, {'id': has_translations.get(data_dict.get('language'))})

    if not trans_res.get('translation_status') == 'published':
        raise p.toolkit.ValidationError('Translation resource in language {0} does not exist'.format(data_dict.get('language')))

    ds = p.toolkit.get_action('datastore_search')(context, {'id':data_dict.get('resource_id')})
    fields = _get_field_ids(ds.get('fields'))

    trans_ds = p.toolkit.get_action('datastore_search')(context, {'id':has_translations.get(data_dict.get('language'))})
    trans_fields = _get_field_ids(trans_ds.get('fields'))
    data_dict.update({'fields':fields, 'translation_fields':trans_fields, 'translation_resource_id':trans_res.get('id')})
    data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']
    pprint.pprint(data_dict)
    #asdf
    # TODO: Create view from res, trans_res with trans_fields
    data_dict = db.get_view(context, data_dict)
    print 'data is'
    print data_dict.get('resource_id')
    data = {'id': data_dict.get('resource_id')}
    extras = data_dict.get('__extras')
    if extras and extras.get('ignore_alias'):
        data.update({'ignore_alias':True})
    print data_dict
    return p.toolkit.get_action('datastore_search')(context, data)
    #create_view(context, data_dict)
    # TODO: pass view to datastore_search or datastore_search_sql to get expected output


def _translate_automatic(context, res, data_dict, ds_dict):
    pass

def _translate_manual(context, res, col_name, original_ds, new_ds):
    # Just update total number of values with None in case overriding
    total = original_ds.get('total')
    columns = json.loads(res.get('translation_columns'))
    for k,v in columns.iteritems():
        if k == col_name:
            columns.update({k:'manual'})

    columns = json.dumps(columns)
    res = p.toolkit.get_action('resource_update')(context, {
            'id': res.get('id'),
            'url': res.get('url'),
            'format': res.get('format'),
            'translation_parent_id': res.get('translation_parent_id'),
            'translation_resource': True,
            'translation_language': res.get('translation_language'),
            'translation_status': res.get('translation_status'),
            'translation_columns':columns,
            })
    return p.toolkit.get_action('datastore_upsert')(context,
            {
                'resource_id': new_ds.get('resource_id'),
                'force':True,
                'method':'upsert',
                'allow_update_with_id':True,
                'records': [{'_id':i, col_name:''} for i in range(1,total+1)]
            })


def _transcript(context, res, col_name, original_ds, new_ds):
    # TODO: Need to json serialize context and data_dict
    print 'HELLO Transliterate'
    res_id = original_ds.get('resource_id')
    total = original_ds.get('total')
    columns = json.loads(res.get('translation_columns'))
    for k,v in columns.iteritems():
        if k == col_name:
            columns.update({k:'transcription'})
    columns = json.dumps(columns)
    res = p.toolkit.get_action('resource_update')(context, {
            'id': res.get('id'),
            'url': res.get('url'),
            'format': res.get('format'),
            'translation_parent_id': res.get('translation_parent_id'),
            'translation_resource': True,
            'translation_language': res.get('translation_language'),
            'translation_status': res.get('translation_status'),
            'translation_columns':columns,
            })
    STEP = 100
    offset = 0
    print total/STEP+1
    for k in range(1,total/STEP+2):
        print 'offset'
        print k
        recs = p.toolkit.get_action('datastore_search')(context, {'resource_id':res_id, 'offset': offset, 'sort':'_id'}).get('records')
        #recs = original_ds.get('records')
        #print original_ds
        #print recs
        #recs = ds.get('records')
        nrecs = []
        for rec in recs:
            key = col_name
            value = rec.get(key)
            nvalue = unidecode(value)
            rec.update({key:nvalue})
            #print 'KEY:VALUE'
            #print key+':'+nvalue
            nrec = {'_id':rec.get('_id'),key:nvalue}
            #print nrec
            nrecs.append(nrec)
            #name = data_dict.get('column_name')

        ds = p.toolkit.get_action('datastore_upsert')(context,
                {
                    'resource_id': new_ds.get('resource_id'),
                    'allow_update_with_id':True,
                    'force': True,
                    'records': nrecs
                    })
        offset=offset+STEP
    return new_ds

def _delete_column(context, col_name, ds, total):
    print 'initializing column..'
    # And update with correct number of records
    return p.toolkit.get_action('datastore_upsert')(context,
            {
                'resource_id': ds.get('resource_id'),
                'force':True,
                'method':'upsert',
                'allow_update_with_id':True,
                'records': [{'_id':i, col_name:None} for i in range(1,total+1)]
            })

def _initialize_column(context, col_name, ds, total):
    print 'initializing column..'
    fields = ds.get('fields')
    # Remove _id from fields list
    fields.pop(0)
    for field in fields:
        if col_name == field.get('id'):
            return

    # Build fields list
    new_column = {'id': col_name,
                'type': 'text'}
    fields.append(new_column)

    # Update fields with datastore_create
    new_ds = p.toolkit.get_action('datastore_create')(context,
            {
                'resource_id': ds.get('resource_id'),
                'force':True,
                'allow_update_with_id':True,
                'fields': fields
                #'records':[{col_name:''}]
                })
    print 'new ds'
    return
    # And update with correct number of records
    #return p.toolkit.get_action('datastore_upsert')(context,
    #        {
    #            'resource_id': ds.get('resource_id'),
    #            'force':True,
    #            'method':'upsert',
    #            'allow_update_with_id':True,
    #            'records': [{'_id':i, col_name:''} for i in range(1,total+1)]
    #        })


#def datastore_make_private(context, data_dict):
#def datastore_make_public(context, data_dict):

def _resource_exists(context, data_dict):
    ''' Returns true if the resource exists in CKAN and in the datastore '''
    model = _get_or_bust(context, 'model')
    res_id = _get_or_bust(data_dict, 'resource_id')
    if not model.Resource.get(res_id):
        return False

    resources_sql = sqlalchemy.text(u'''SELECT 1 FROM "_table_metadata"
                                        WHERE name = :id AND alias_of IS NULL''')
    results = db._get_engine(data_dict).execute(resources_sql, id=res_id)
    return results.rowcount > 0

def _get_field_ids(field_arr):
    l = []
    for it in field_arr:
        #if not it['id'] == '_id':
        l.append(it['id'])
    return l

def _check_read_only(context, data_dict):
    ''' Raises exception if the resource is read-only.
    Make sure the resource id is in resource_id
    '''
    if data_dict.get('force'):
        return
    res = p.toolkit.get_action('resource_show')(
        context, {'id': data_dict['resource_id']})
    if res.get('url_type') != 'datastore':
        raise p.toolkit.ValidationError({
            'read-only': ['Cannot edit read-only resource. Either pass'
                          '"force=True" or change url-type to "datastore"']
        })
