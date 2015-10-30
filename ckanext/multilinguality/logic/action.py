import logging
import os
import shlex

import pylons
import sqlalchemy
import json
import pprint

from unidecode import unidecode
import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as p
import ckanext.multilinguality.logic.schema as dsschema
import ckanext.multilinguality.vocabularies as closed_vocabularies

import uuid

PAGE_STEP = 100

#from ckan.lib.celery_app import celery
if not os.environ.get('DATASTORE_LOAD'):
    import paste.deploy.converters as converters
    ValidationError = p.toolkit.ValidationError
else:
    log.warn("Running datastore without CKAN")

    class ValidationError(Exception):
        def __init__(self, error_dict):
            pprint.pprint(error_dict)

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
    has_translations = json.loads(res.get('has_translations','{}'))
    orig_language = res.get('language', 'en')
    if orig_language == data_dict.get('language'):
        raise p.toolkit.ValidationError('Cannot translate resource {0} in origin language {1}'.format(data_dict.get('id'),data_dict.get('language')))
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
    columns_status = {}
    for field in fields:
        col = {field.get('id')}
        if field.get('type') != 'text':
            columns_status.update({field.get('id'):'no-translate'})
        else:
            columns_status.update({field.get('id'):''})

    columns_status = json.dumps(columns_status)

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
                'translation_columns_status':columns_status,
                'translation_columns': '{}',
            })

    # Update original resource metadata
    has_translations.update({data_dict.get('language'):new_res.get('id')})
    res.update({
            'has_translations': json.dumps(has_translations),
            'language': res.get('language', 'en'),
            })
    res = p.toolkit.get_action('resource_update')(context, res)

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
    print 'Updating...'
    print data_dict
    #records = data_dict.pop('records', None)
    data_dict, errors = _validate(data_dict, schema, context)
    #if records:
    #    data_dict['records'] = records
    if errors:
        raise p.toolkit.ValidationError(errors)
    print 'after validate'

    original_res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})
    print 'after show'
    print original_res
    # Check if candidate resource is translation resource
    if original_res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is translation resource, please provide original resource id'.format(original_res.get('id')))

    language = data_dict.get('language')

    has_translations = json.loads(original_res.get('has_translations','{}'))
    orig_language = original_res.get('language', 'en')
    if orig_language == language:
        raise p.toolkit.ValidationError('Cannot update resource {0} in original language {1}'.format(data_dict.get('resource_id'),language))
    if not language in has_translations.keys():
        log.info('Resource {0} in language {1} doesn\'t exists'.format(data_dict.get('resource_id'), language))
        raise p.toolkit.ValidationError('Translation resource in language {0} doesn\'t exist'.format(language))
    
    resource_id = has_translations.get(language)
    res = p.toolkit.get_action('resource_show')(context, {'id': resource_id})
    
    ds = p.toolkit.get_action('datastore_search')(context, {'resource_id': res.get('id')})
    original_ds = p.toolkit.get_action('datastore_search')(context, {'resource_id': original_res.get('id')})

    # Check if column_name exists in original table
    col_name = data_dict.get('column_name')
    title_translation = data_dict.get('title_translation')
    field_exists = False
    for field in original_ds.get('fields'):
        if field['id'] == col_name:
            field_exists = True
            break
    if not field_exists:
        raise p.toolkit.ValidationError(u'Column name "{0}" does not correspond to any "{1}" table columns'.format(data_dict.get('column_name'),res.get('translation_parent_id')))


    mode = data_dict.get('mode')
    #if mode == 'title':
        #translation_columns = json.loads(res.get('translation_columns', '{}'))
        #if not translation_columns.get(col_name):
    #    translation = data_dict.get('translation')
    #    if not 'translation' in data_dict:
    #        raise p.toolkit.ValidationError('No translation provided for column {0}'.format(col_name))
    #    print 'translation'
    #    print data_dict.get('translation')
    #    return _update_title(context, res, translation, col_name )
    #else:
    if mode == 'manual':
        _initialize_column(context, col_name, ds, original_ds.get('total'))
        return _translate_manual(context, res, col_name, original_ds, ds)
    elif mode == 'automatic':
        _initialize_column(context, col_name, ds, original_ds.get('total'))
        return _translate_automatic(context, res, col_name, original_ds, ds)
    elif mode == 'transcription':
        _initialize_column(context, col_name, ds, original_ds.get('total'))
        _transcript(context, res, col_name, original_ds, ds)
    elif mode == 'title':
        _update_title(context, res, col_name, title_translation)
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

    #if not res.get('translation_resource'):
    #    raise p.toolkit.ValidationError('Resource "{0}" is not a translation resource'.format(res.get('id')))

    #original_res = p.toolkit.get_action('resource_show')(context, {'id': res.get('translation_parent_id')})
    original_res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    if original_res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is translation resource, please provide original resource id'.format(res.get('id')))

    language = data_dict.get('language')

    has_translations = json.loads(original_res.get('has_translations','{}'))
    orig_language = original_res.get('language', 'en')
    if orig_language == language:
        raise p.toolkit.ValidationError('Cannot update resource {0} in original language {1}'.format(data_dict.get('resource_id'),language))
    if not language in has_translations.keys():
        log.info('Resource {0} in language {1} doesn\'t exists'.format(data_dict.get('resource_id'), language))
        raise p.toolkit.ValidationError('Translation resource in language {0} doesn\'t exist'.format(language))

    resource_id = has_translations.get(language)
    res = p.toolkit.get_action('resource_show')(context, {'id': resource_id})


    # Delete column if option is set
    # TODO: datastore doesnt support deleting a whole column - dont support this
    filters = {}
    if 'column_name' in data_dict:
        #filters = {data_dict.get('column_name'):'*'}
        # Delete datastore table
        print 'Delete only column!'

        ds = p.toolkit.get_action('datastore_search')(context, {'id': resource_id})
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

        columns = json.loads(res.get('translation_columns_status','{}'))
        for k,v in columns.iteritems():
            if k == col_name:
                columns.update({k:'no-translate'})

        columns = json.dumps(columns)

        res.update({
                'translation_columns_status':columns,
            })
        res = p.toolkit.get_action('resource_update')(context, res)

        print 'ASDASADSD'
        filters = {col_name:'*'}
        #la = _delete_column(context, data_dict.get('column_name'), ds, total)
        #return
        print 'after initialize'
        print col_name
        #pprint.pprint(la)
        #filters = {}
        return p.toolkit.get_action('datastore_delete')(context, {'resource_id': resource_id, 'filters':filters, 'force':True})

    # Delete datastore table
    try:
        p.toolkit.get_action('datastore_delete')(context, {'resource_id': resource_id, 'filters':filters, 'force':True})
    except:
        return

    # Update metadata and delete resouce
    try:
        has_translations = json.loads(original_res.get('has_translations'))
    except p.toolkit.ValidationError:
        log.info('Original resource has no translation metadata. Something went wrong...')

    del has_translations[res.get('translation_language')]
    
    original_res.update({
                    json.dumps(has_translations)
                    })
    upd_original_res = p.toolkit.get_action('resource_update')(context, original_res)
    return p.toolkit.get_action('resource_delete')(context, {'id': resource_id})

def translate_resource_publish(context, data_dict):
    '''Publishes the translation resource
    by changing its state
    '''
    p.toolkit.check_access('translate_resource_publish', context, data_dict)

    schema = context.get('schema', dsschema.translate_resource_publish_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    #package = p.toolkit.get_action('dataset_show')(context, {'id': data_dict.get('package_id')})
    #res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    original_res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    if original_res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is translation resource, please provide original resource id'.format(res.get('id')))

    language = data_dict.get('language')

    has_translations = json.loads(original_res.get('has_translations','{}'))
    orig_language = original_res.get('language', 'en')
    
    if orig_language == language:
        raise p.toolkit.ValidationError('Cannot update resource {0} in original language {1}'.format(data_dict.get('resource_id'),language))
    if not language in has_translations.keys():
        log.info('Resource {0} in language {1} doesn\'t exists'.format(data_dict.get('resource_id'), language))
        raise p.toolkit.ValidationError('Translation resource in language {0} doesn\'t exist'.format(language))

    resource_id = has_translations.get(language)
    res = p.toolkit.get_action('resource_show')(context, {'id': resource_id})



    if not res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is not a translation resource'.format(res.get('id')))

    # Update resource metadata
    res.update({
        'translation_status': 'published'
        })

    res = p.toolkit.get_action('resource_update')(context, res)
    return res

def translate_resource_unpublish(context, data_dict):
    '''Unpublishes the translation resource
        by changing its state
    '''
    p.toolkit.check_access('translate_resource_publish', context, data_dict)

    schema = context.get('schema', dsschema.translate_resource_publish_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    print 'errors'
    print errors
    if errors:
        raise p.toolkit.ValidationError(errors)
    #package = p.toolkit.get_action('dataset_show')(context, {'id': data_dict.get('package_id')})
    #res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    original_res = p.toolkit.get_action('resource_show')(context, {'id': data_dict.get('resource_id')})

    if original_res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is translation resource, please provide original resource id'.format(original_res.get('id')))

    language = data_dict.get('language')

    has_translations = json.loads(original_res.get('has_translations','{}'))
    orig_language = original_res.get('language', 'en')

    if orig_language == language:
        raise p.toolkit.ValidationError('Cannot update resource {0} in original language {1}'.format(data_dict.get('resource_id'),language))
    if not language in has_translations.keys():
        log.info('Resource {0} in language {1} doesn\'t exists'.format(data_dict.get('resource_id'), language))
        raise p.toolkit.ValidationError('Translation resource in language {0} doesn\'t exist'.format(language))

    resource_id = has_translations.get(language)
    res = p.toolkit.get_action('resource_show')(context, {'id': resource_id})

    if not res.get('translation_resource'):
        raise p.toolkit.ValidationError('Resource "{0}" is not a translation resource'.format(res.get('id')))

    # Update resource metadata
    res.update({
        'translation_status': 'draft'
        })
    print 'RESOUREEEECE'
    print res
    res = p.toolkit.get_action('resource_update')(context, res)
    return res


@logic.side_effect_free
def translate_resource_search(context, data_dict):
    '''Search translation resources given resource_id, language and datastore_search filters?'''
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


    # if resource asked in original language return it
    if data_dict.get('language') == res.get('language'):
        return p.toolkit.get_action('datastore_search')(context, data_dict)

    has_translations = json.loads(res.get('has_translations', '{}'))
    if not data_dict.get('language') in has_translations.keys():
        raise p.toolkit.ValidationError('Translation resource in language {0} does not exist'.format(data_dict.get('language')))
    trans_res = p.toolkit.get_action('resource_show')(context, {'id': has_translations.get(data_dict.get('language'))})
    print data_dict
    if (not data_dict.get('edit_mode') and not trans_res.get('translation_status') == 'published'):
        raise p.toolkit.ValidationError('Translation resource in language {0} does not exist'.format(data_dict.get('language')))

    ds = p.toolkit.get_action('datastore_search')(context, {'id':data_dict.get('resource_id')})

    original_fields = _get_field_ids(ds.get('fields'))
    print _get_list(data_dict.get('fields'))
    if data_dict.get('fields'):
        for field in _get_list(data_dict.get('fields')):
            if not field in original_fields:
                raise p.toolkit.ValidationError('Requested field {0} does not exist in resource {1} table'.format(field, data_dict.get('resource_id')))

    trans_ds = p.toolkit.get_action('datastore_search')(context, {'id':has_translations.get(data_dict.get('language'))})
    trans_fields = _get_field_ids(trans_ds.get('fields'))
    trans_columns = json.loads(trans_res.get("translation_columns"))
    trans_columns_status = json.loads(trans_res.get("translation_columns_status"))

    data_dict.update({'original_fields':original_fields, 'translation_fields':trans_fields, 'translation_resource_id':trans_res.get('id'), 'translation_columns':trans_columns, 'translation_columns_status':trans_columns_status})

    # TODO: Create view from res, trans_res with trans_fields
    #data_dict = db.get_view(context, data_dict)
    #data = {'id': data_dict.get('resource_id'),'ignore_alias':True}
    #if extras:
    #    data.update(extras)
    if data_dict.get('edit_mode'):
        data = {'sql': _create_view_edit(context, data_dict)}
    else:
        data = {'sql': _create_view(context, data_dict)}

    ds_search_sql = p.toolkit.get_action('datastore_search_sql')(context, data)

    params_dict = _get_params_dict(data_dict)
    ds_search_sql.update(params_dict)
    # hide sql field from result
    del ds_search_sql['sql']
    return ds_search_sql

def _create_view(context, data_dict):
    '''Create view from combination of fields.'''

    orig_resource = data_dict.get('resource_id')
    trans_resource = data_dict.get('translation_resource_id')

    all_fields = data_dict.get('original_fields',[])
    trans_columns = data_dict.get('translation_columns',[])
    selected_fields = data_dict.get('fields', all_fields)
    field_ids = _get_fields(selected_fields, data_dict)
    sql_fields = u", ".join(field_ids)

    limit = data_dict.get('limit', 100)
    offset = data_dict.get('offset', 0)
    sort = _sort(context, data_dict, [trans_columns[f] if f in trans_columns else f for f in all_fields])
    #ts_query, rank_column = _textsearch_query(data_dict)
    #where = _where(all_fields, data_dict)

    sql_string = u'''SELECT {fields},
            COUNT(*) OVER() AS "_full_count"
            FROM "{orig_resource}"
            INNER JOIN "{trans_resource}"
            ON "{orig_resource}"._id = "{trans_resource}"._id
            {sort}
            OFFSET {offset}
            LIMIT {limit};'''.format(
    fields=sql_fields,
    #rank=rank_column,
    orig_resource=orig_resource,
    trans_resource=trans_resource,
    #query=ts_query,
    #where=where,
    sort=sort,
    offset=offset,
    limit=limit
    )
    #sql_string = sql_string.replace('%', '%%')
    #sql_string = sql_string.format(where=where_clause), [where_values]
    #print sql_string
    #asd
    return sql_string
 
def _create_view_edit(context, data_dict):
    '''Create view for edit from combination of fields.'''

    orig_resource = data_dict.get('resource_id')
    trans_resource = data_dict.get('translation_resource_id')

    all_fields = data_dict.get('original_fields',[])
    #all_fields += data_dict.get('translation_fields', [])
    trans_columns = data_dict.get('translation_columns',[])
    selected_fields = data_dict.get('fields', all_fields)
    field_ids = _get_fields_edit(selected_fields, data_dict)
    sql_fields = u", ".join(field_ids)

    limit = data_dict.get('limit', 100)
    offset = data_dict.get('offset', 0)
    sort = _sort(context, data_dict, [f for f in all_fields])
    #ts_query, rank_column = _textsearch_query(data_dict)
    #where = _where(all_fields, data_dict)

    sql_string = u'''SELECT {fields},
            COUNT(*) OVER() AS "_full_count"
            FROM "{orig_resource}"
            INNER JOIN "{trans_resource}"
            ON "{orig_resource}"._id = "{trans_resource}"._id
            {sort}
            OFFSET {offset}
            LIMIT {limit};'''.format(
    fields=sql_fields,
    #rank=rank_column,
    orig_resource=orig_resource,
    trans_resource=trans_resource,
    #query=ts_query,
    #where=where,
    sort=sort,
    offset=offset,
    limit=limit
    )
    #sql_string = sql_string.replace('%', '%%')
    #sql_string = sql_string.format(where=where_clause), [where_values]
    #print sql_string
    #asd
    return sql_string
    
def _get_fields(fields, data_dict):
    #orig_field_ids = data_dict.get('fields', [])
    trans_field_ids = data_dict.get('translation_fields', [])

    orig_table = data_dict.get('resource_id')
    trans_table = data_dict.get('translation_resource_id')
    #extras = data_dict.get('__extras', {})
    #if trans_fields_ids:
    #    all_field_ids = _get_list(fields)
    #for field in all_field_ids:
    #        if not field in orig_field_ids:
    #            raise ValidationError({
    #                'fields': [u'field "{0}" not in table'.format(field)]}
    #            )
    #else:
    #    all_field_ids = orig_field_ids

    all_field_ids = _get_list(fields)
    print 'orig field ids'
    print all_field_ids
    print 'trans field ids'
    print trans_field_ids
    translation_columns = data_dict.get('translation_columns')
    print 'trans columns'
    print translation_columns
    field_ids = []
    for tf in all_field_ids:
        if tf in trans_field_ids and not tf == '_id':
            table = trans_table
        else:
            table = orig_table
        # if column translation available rename field using alias
        if tf in translation_columns:
            field_ids.append(u'"{0}"."{1}" AS "{2}"'.format(table, tf, translation_columns.get(tf)))
        else:
            field_ids.append(u'"{0}"."{1}"'.format(table, tf))
    print 'final fields'
    print field_ids
    return field_ids

def _get_fields_edit(fields, data_dict):
    #orig_field_ids = data_dict.get('fields', [])
    trans_field_ids = data_dict.get('translation_fields', [])

    orig_table = data_dict.get('resource_id')
    trans_table = data_dict.get('translation_resource_id')
    #extras = data_dict.get('__extras', {})
    #if trans_fields_ids:
    #    all_field_ids = _get_list(fields)
    #for field in all_field_ids:
    #        if not field in orig_field_ids:
    #            raise ValidationError({
    #                'fields': [u'field "{0}" not in table'.format(field)]}
    #            )
    #else:
    #    all_field_ids = orig_field_ids

    all_field_ids = _get_list(fields)
    print 'orig field ids'
    print all_field_ids
    print 'trans field ids'
    print trans_field_ids
    translation_columns = data_dict.get('translation_columns')
    translation_columns_status = data_dict.get('translation_columns_status')
    print 'trans columns'
    print translation_columns
    field_ids = []
    for tf in all_field_ids:
        if tf in trans_field_ids and not tf == '_id':
            table = trans_table
        else:
            table = orig_table
        # if column translation available rename field using alias
        field_ids.append(u'"{0}"."{1}"'.format(orig_table, tf))
        if not translation_columns_status.get(tf) == 'no-translate':
            field_ids.append(u'"{0}"."{1}" AS "{2}"'.format(table, tf, tf+'-'+data_dict.get('language')))
    print 'final fields'
    print field_ids
    return field_ids


def _get_params_dict(data_dict):
    params_dict = {}
    for param in ['language', 'limit', 'offset', 'fields', 'sort', 'filters', 'q']:
        if param in data_dict:
            params_dict[param] = data_dict.get(param)
    return params_dict

### Copy from datastore start
def _validate_int(i, field_name, non_negative=False):
    try:
        i = int(i)
    except ValueError:
        raise ValidationError({
            field_name: ['{0} is not an integer'.format(i)]
        })
    if non_negative and i < 0:
        raise ValidationError({
            field_name: ['{0} is not a non-negative integer'.format(i)]
        })

def _get_list(input, strip=True):
    '''Transforms a string or list to a list'''
    if input is None:
        return
    if input == '':
        return []

    l = converters.aslist(input, ',', True)
    if strip:
        return [_strip(x) for x in l]
    else:
        return l

def _where(field_ids, data_dict):
    '''Return a SQL WHERE clause from data_dict filters and q'''
    filters = data_dict.get('filters', {})

    if not isinstance(filters, dict):
        raise ValidationError({
            'filters': ['Not a json object']}
        )

    where_clauses = []
    values = []

    for field, value in filters.iteritems():
        print field
        print value
        if field not in field_ids:
            raise ValidationError({
                'filters': ['field "{0}" not in table'.format(field)]}
            )
        if isinstance(value, list):
            vals = []
            for v in value:
                vals.append(u'"{0}"."{1}" LIKE "%{2}%"'.format(data_dict.get('resource_id'), field, v))
            val = u'({0})'.format(u' OR '.join(vals))
        else:
            val = u'"{0}"."{1}" LIKE "%{2}%"'.format(data_dict.get('resource_id'), field, value)
        where_clauses.append(val)
        #where_clauses.append(u'"{0}" = {1}'.format(field, val))
        values.append(value)

    # add full-text search where clause
    if data_dict.get('q'):
        where_clauses.append(u'_full_text @@ query')

    #where_clause = u' AND '.join(where_clauses)
    where_clause = u'({0})'.format(u' AND '.join(where_clauses))
    if where_clause:
        where_clause = u'WHERE ' + where_clause
    #where_clause.replace('%%', '%') 
    #where_clause = where_clause.replace('%', '%%')
    #if where_values:
    #    where = u'{0}'.format(where_clause)
    #    for wv in where_values:
    #        where += u'"{0}"'.format(wv)
    #else:
    #    where = u''
    #print where_clause
    return where_clause


def _textsearch_query(data_dict):
    q = data_dict.get('q')
    lang = data_dict.get(u'language', u'english')
    lang = u'english'
    if q:
        if data_dict.get('plain', True):
            statement = u", plainto_tsquery('{lang}', '{query}') query"
        else:
            statement = u", to_tsquery('{lang}', '{query}') query"

        rank_column = u', ts_rank(_full_text, query, 32) AS rank'
        print statement.format(lang=lang, query=q), rank_column
        return statement.format(lang=lang, query=q), rank_column
    return '', ''

def _sort(context, data_dict, field_ids):
    sort = data_dict.get('sort')
    if not sort:
        if data_dict.get('q'):
            return u'ORDER BY rank'
            #return u''
        else:
            return u''

    resource_id = data_dict.get('resource_id')
    clauses = _get_list(sort, False)

    clause_parsed = []
    print clauses
    for clause in clauses:
        print clause
        clause = clause.encode('utf-8')
        clause_parts = shlex.split(clause)
        if len(clause_parts) == 1:
            field, sort = clause_parts[0], 'asc'
        elif len(clause_parts) == 2:
            field, sort = clause_parts
        else:
            raise ValidationError({
                'sort': ['not valid syntax for sort clause']
            })
        field, sort = unicode(field, 'utf-8'), unicode(sort, 'utf-8')

        if field not in field_ids:
            raise ValidationError({
                'sort': [u'field "{0}" not in table with fields {1}'.format(
                    field, field_ids)]
            })
        if sort.lower() not in ('asc', 'desc'):
            raise ValidationError({
                'sort': ['sorting can only be asc or desc']
            })
        print 'before'
        print clause_parsed
        clause_parsed.append(u'"{0}" {1}'.format(
            field, sort)
        )
        print 'after'
        print clause_parsed

    if clause_parsed:
        return "order by " + ", ".join(clause_parsed)

def _strip(input):
    if isinstance(input, basestring) and len(input) and input[0] == input[-1]:
        return input.strip().strip('"')
    return input

### Copy from datastore end

def _translate_automatic(context, res, col_name, original_ds, new_ds):
    total = original_ds.get('total')
    res_id = original_ds.get('resource_id')
    columns = json.loads(res.get('translation_columns_status','{}'))
    for k,v in columns.iteritems():
        if k == col_name:
            columns.update({k:'automatic'})

    columns = json.dumps(columns)
    res.update({
            'translation_columns_status' : columns
            })
    res = p.toolkit.get_action('resource_update')(context, res)

    vocs = closed_vocabularies.get_names()

    offset = 0
    iters = total/PAGE_STEP
    if not (total % PAGE_STEP == 0):
        iters += 1
    print iters
    for k in range(1,iters+1):
        print 'offset'
        print k

        recs = p.toolkit.get_action('datastore_search')(context, {'resource_id':res_id, 'offset': offset, 'limit': PAGE_STEP, 'sort':'_id'}).get('records')
        nrecs = []
        for rec in recs:
            key = col_name
            value = rec.get(key)

            nvalue = ''
            found = False
            # look for term in all available vocabularies
            for voc_name in vocs:
                voc = closed_vocabularies.get_by_name(voc_name)
                voc = voc.get('vocabulary')
                for term in voc:
                    term_key = term.value
                    term_value = term.title
                    if term_key == value:
                        nvalue = term_value
                        found = True
                        break
                if found:
                    break

            rec.update({key:nvalue})
            nrec = {'_id':rec.get('_id'),key:nvalue}
            nrecs.append(nrec)

        ds = p.toolkit.get_action('datastore_upsert')(context,
                {
                    'resource_id': new_ds.get('resource_id'),
                    'allow_update_with_id':True,
                    'force': True,
                    'records': nrecs
                    })
        offset=offset+PAGE_STEP
    return new_ds

def _update_title(context, res, col_name, title_translation):
    columns = json.loads(res.get('translation_columns','{}'))

    if title_translation:
        columns.update({col_name: title_translation})
    columns = json.dumps(columns)

    res.update({
            'translation_columns': columns,
            })

    res = p.toolkit.get_action('resource_update')(context, res)
    return res

def _translate_manual(context, res, col_name, original_ds, new_ds):
    # Just update total number of values with None in case overriding
    total = original_ds.get('total')
    columns = json.loads(res.get('translation_columns_status','{}'))
    for k,v in columns.iteritems():
        if k == col_name:
            columns.update({k:'manual'})

    columns = json.dumps(columns)
    res.update({
            'translation_columns_status' : columns
            })
    res = p.toolkit.get_action('resource_update')(context, res)
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
    res_id = original_ds.get('resource_id')
    total = original_ds.get('total')
    columns = json.loads(res.get('translation_columns_status','{}'))
    for k,v in columns.iteritems():
        if k == col_name:
            columns.update({k:'transcription'})
    columns = json.dumps(columns)
    res.update({
            'translation_columns_status': columns,
            })
    res = p.toolkit.get_action('resource_update')(context, res)
    
    offset = 0
    iters = total/PAGE_STEP
    if not (total % PAGE_STEP == 0):
        iters += 1
    print iters
    for k in range(1,iters+1):
        print 'offset'
        print k
        recs = p.toolkit.get_action('datastore_search')(context, {'resource_id':res_id, 'offset': offset, 'limit': PAGE_STEP, 'sort':'_id'}).get('records')

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
        offset=offset+PAGE_STEP
    return new_ds

def _delete_column(context, col_name, ds, total):
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
    print 'fields'
    print fields
    print 'before datastore create'
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
