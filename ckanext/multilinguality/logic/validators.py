import ckan.plugins as p
from ckan.common import _

def datastore_table_exists(value, context):
    print 'DATASTORE EXISTS?'
    print 'context'
    print context
    model = context['model']
    session = context['session']
    result = session.query(model.Resource).get(value)
    print 'res'
    print result
    if not result:
        raise p.toolkit.ObjectNotFound('%s: %s' % (_('Not found'), _('Resource')))
    return value

    return value
