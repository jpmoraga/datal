# -*- coding: utf-8 -*-
from core.exceptions import SearchIndexNotFoundException
from core import settings
from core.daos.resource import AbstractDataStreamDBDAO
from core.models import DatastreamI18n


class DataStreamDBDAO(AbstractDataStreamDBDAO):
    """ class for manage access to datastreams' database tables """

    def query(self, account_id=None, language=None, page=0, itemsxpage=settings.PAGINATION_RESULTS_PER_PAGE,
              sort_by='-id', filters_dict=None, filter_name=None, exclude=None):

        return super(DataStreamDBDAO, self).query(account_id, language, page, itemsxpage,
                                                  sort_by, filters_dict, filter_name, exclude)

class DatastreamSearchDAOFactory():
    """ select Search engine"""
    
    def create(self):
        if settings.USE_SEARCHINDEX == 'searchify':
            self.search_dao = DatastreamSearchifyDAO()
        else:
            raise SearchIndexNotFoundException() #TODO define this error

        return self.search_dao
        
        
class DatastreamSearchifyDAO():
    """ class for manage access to datasets' searchify documents """
    def __init__(self):
        from core.lib.indexers.searchify import SearchifyIndex
        self.search_index = SearchifyIndex()
        
    def add(self, datastream_revision, language):

        import time

        tags = datastream_revision.tagdataset_set.all().values_list('tag__name')
        # Get category name
        category = datastream_revision.category.categoryi18n_set.get(language=language)
        datastreami18n = DatastreamI18n.objects.get(datastream_revision=datastream_revision, language=language)


        text = [datastreami18n.title, datastreami18n.description, datastream_revision.user.nick, datastream_revision.datastream.guid]
        text.extend(tags) # datastream has a table for tags but seems unused. I define get_tags funcion for dataset.
        text = ' '.join(text)


        document = {
                'docid' : "DS::" + str(datastream_revision.datastream.guid),
                'fields' :
                    {'type' : 'ds',
                     'datastream_id': datastream_revision.datastream.id,
                     'datastream__revision_id': datastream_revision.id,
                     'title': datastreami18n.title,
                     'text': text,
                     'description': datastreami18n.description,
                     'owner_nick' :datastream_revision.user.nick,
                     'tags' : ','.join(tags),
                     'account_id' : datastream_revision.datastream.account.id,
                     'parameters': "",
                     'timestamp': int(time.mktime(datastream_revision.created_at.timetuple())),
                     'end_point': datastream_revision.dataset.end_point,
                    },
                'categories': {'id': unicode(category.id), 'name': category.name}
                }

        # Update dict with facets
        # try:
        #     document = add_facets_to_doc(self, account, document)
        # except Exception, e:
        #     logger.error("indexable_dict ERROR: [%s]" % str(e))

        # document['fields'].update(get_meta_data_dict(datastream.meta_text))

        self.search_index.indexit(document)
        
    def remove(self, datastream_revision):
        self.search_index.delete_documents(["DS::" + str(datastream_revision.datastream.guid)])
        
