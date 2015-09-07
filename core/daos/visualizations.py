# -*- coding: utf-8 -*-
import operator
import time
import logging
import json

from django.db.models import Q, F
from django.db import connection, IntegrityError
from django.db.models import Count
from django.core.serializers.json import DjangoJSONEncoder

from datetime import datetime, date, timedelta
from core.utils import slugify
from core import settings
from core.cache import Cache
from core.daos.resource import AbstractVisualizationDBDAO
from core.models import VisualizationRevision, VisualizationHits, VisualizationI18n, Preference, Visualization
from core.exceptions import SearchIndexNotFoundException
from core.lib.searchify import SearchifyIndex
from core.lib.elastic import ElasticsearchIndex
from core.choices import STATUS_CHOICES, StatusChoices
from core.builders.visualizations import VisualizationImplBuilder

from datetime import date, timedelta

logger = logging.getLogger(__name__)


class VisualizationDBDAO(AbstractVisualizationDBDAO):
    """ class for manage access to visualizations database tables """
    def __init__(self):
        pass

    def create(self, visualization=None, datastream_rev=None, user=None, language=None, **fields):
        """create a new visualization if needed and a visualization_revision"""

        if not visualization:
            # Create a new datastream (TITLE is for automatic GUID creation)
            visualization = Visualization.objects.create(
                user=user,
                title=fields['title'],
                datastream=datastream_rev.datastream
            )

        visualization_rev = VisualizationRevision.objects.create(
            datastream_revision=datastream_rev,
            visualization=visualization,
            user=user,
            status=StatusChoices.DRAFT,
            lib=fields['lib'],
            impl_details=VisualizationImplBuilder(**fields).build()
        )
        logger.info(visualization_rev.impl_details)

        visualization_i18n = VisualizationI18n.objects.create(
            visualization_revision=visualization_rev,
            language=language,
            title=fields['title'].strip().replace('\n', ' '),
            description=fields['description'].strip().replace('\n', ' '),
            notes=fields['notes'].strip()
        )

        return visualization, visualization_rev

    def get(self, language, visualization_id=None, visualization_revision_id=None, guid=None, published=True):
        """ Get full data """

        fld_revision_to_get = 'visualization__last_published_revision' if published else 'visualization__last_revision'

        if guid:
            visualization_revision = VisualizationRevision.objects.select_related().get(
                visualization__guid=guid,
                pk=F(fld_revision_to_get),
                user__language=language,
                visualizationi18n__language=language
            )
        elif not visualization_id:
            visualization_revision = VisualizationRevision.objects.select_related().get(
                pk=visualization_revision_id,
                user__language=language,
                visualizationi18n__language=language
            )
        else:
            visualization_revision = VisualizationRevision.objects.select_related().get(
                pk=F(fld_revision_to_get),
                user__language=language,
                visualizationi18n__language=language
            )

        tags = visualization_revision.datastream_revision.tagdatastream_set.all().values(
            'tag__name',
            'tag__status',
            'tag__id'
        )
        sources = visualization_revision.datastream_revision.sourcedatastream_set.all().values(
            'source__name',
            'source__url',
            'source__id'
        )
        parameters = []

        # Get category name
        category = visualization_revision.datastream_revision.category.categoryi18n_set.get(language=language)
        visualizationi18n = VisualizationI18n.objects.get(
            visualization_revision=visualization_revision,
            language=language
        )

        # Muestro el link del micrositio solo si esta publicada la revision
        public_url = ''
        if visualization_revision.visualization.last_published_revision:
            domain = visualization_revision.user.account.get_preference('account.domain')
            if not domain.startswith('http'):
                domain = 'http://' + domain
            public_url = '{}/visualizations/{}/{}'.format(domain, visualization_revision.visualization.id, slugify(visualizationi18n.title))

        visualization = dict(
            visualization=visualization_revision.visualization,
            visualization_id=visualization_revision.visualization.id,
            visualization_revision_id=visualization_revision.id,
            user_id=visualization_revision.user.id,
            author=visualization_revision.user.nick,
            account_id=visualization_revision.user.account.id,
            category_id=category.id,
            category_name=category.name,
            status=visualization_revision.status,
            meta_text=visualization_revision.meta_text,
            guid=visualization_revision.visualization.guid,
            impl_details=visualization_revision.impl_details,
            created_at=visualization_revision.created_at,
            last_revision_id=visualization_revision.visualization.last_revision_id,
            last_published_date=visualization_revision.visualization.last_published_revision_date,
            title=visualizationi18n.title,
            description=visualizationi18n.description,
            notes=visualizationi18n.notes,
            tags=tags,
            sources=sources,
            parameters=parameters,
            public_url=public_url,
            slug=slugify(visualizationi18n.title),
            lib=visualization_revision.lib,
            datastream_id=visualization_revision.visualization.datastream.id,
            datastream_revision_id=visualization_revision.datastream_revision_id
        )

        return visualization

    def query_childs(self, visualization_id, language):
        """ Devuelve la jerarquia completa para medir el impacto """

        related = dict(
            dashboards=dict()
        )
        return related

    def update(self, visualization_revision, changed_fields, **fields):
        pass

    def query(self, account_id=None, language=None, page=0, itemsxpage=settings.PAGINATION_RESULTS_PER_PAGE,
          sort_by='-id', filters_dict=None, filter_name=None, exclude=None):
        """ Consulta y filtra las visualizaciones por diversos campos """

        query = VisualizationRevision.objects.filter(
            id=F('visualization__last_revision'),
            visualization__user__account=account_id,
            visualization__user__language=language
        )

        if exclude:
            query.exclude(**exclude)

        if filter_name:
            query = query.filter(visualizationi18n__title__icontains=filter_name)

        if filters_dict:
            predicates = []
            for filter_class, filter_value in filters_dict.iteritems():
                if filter_value:
                    predicates.append((filter_class + '__in', filter_value))
            q_list = [Q(x) for x in predicates]
            if predicates:
                query = query.filter(reduce(operator.and_, q_list))

        total_resources = query.count()
        query = query.values(
            'status',
            'id',
            'visualization__id',
            'visualization__guid',
            'visualization__user__nick',
            'visualization__last_revision_id',
            'visualization__datastream__id',
            'visualization__datastream__last_revision__id',
            'visualization__datastream__last_revision__category__id',
            'visualization__datastream__last_revision__category__categoryi18n__name',
            'visualization__datastream__last_revision__datastreami18n__title',
            'visualizationi18n__title',
            'visualizationi18n__description', 'created_at', 'visualization__user__id',
        )

        query = query.order_by(sort_by)

        # Limit the size.
        nfrom = page * itemsxpage
        nto = nfrom + itemsxpage
        query = query[nfrom:nto]

        return query, total_resources

    def query_filters(self, account_id=None, language=None):
        """
        Reads available filters from a resource array. Returns an array with objects and their
        i18n names when available.
        """
        query = VisualizationRevision.objects.filter(
            id=F('visualization__last_revision'),
            visualization__user__account=account_id,
            visualizationi18n__language=language,
            visualization__datastream__last_revision__category__categoryi18n__language=language
        )

        query = query.values('visualization__user__nick', 'status',
                             'visualization__datastream__last_revision__category__categoryi18n__name')

        filters = set([])

        for res in query:
            status = res.get('status')

            filters.add(('status', status,
                unicode(STATUS_CHOICES[status])
                ))
            if 'visualization__datastream__last_revision__category__categoryi18n__name' in res:
                filters.add(('category', res.get('visualization__datastream__last_revision__category__categoryi18n__name'),
                    res.get('visualization__datastream__last_revision__category__categoryi18n__name')))
            if res.get('visualization__user__nick'):
                filters.add(('author', res.get('visualization__user__nick'),
                    res.get('visualization__user__nick')))

        return [{'type':k, 'value':v, 'title':title} for k,v,title in filters]


class VisualizationHitsDAO():
    """class for manage access to Hits in DB and index"""

    doc_type = "vz"
    from_cache = False

    # cache ttl, 1 hora
    TTL=3600 

    def __init__(self, visualization):
        self.visualization=visualization
        self.search_index = ElasticsearchIndex()
        self.logger=logging.getLogger(__name__)
        self.cache=Cache()

    def add(self,  channel_type):
        """agrega un hit al datastream. """

        try:
            hit=VisualizationHits.objects.create(visualization_id=self.visualization.visualization_id, channel_type=channel_type)
        except IntegrityError:
            # esta correcto esta excepcion?
            raise VisualizationNotFoundException()

        self.logger.info("VisualizationHitsDAO hit! (guid: %s)" % ( self.datastream.guid))

        # armo el documento para actualizar el index.
        doc={'docid':"%s::%s" % (self.doc_type.upper(), self.visualization.guid),
                "type": self.doc_type,
                "script": "ctx._source.fields.hits+=1"}

        return self.search_index.update(doc)

    def count(self):
        return VisualizationHits.objects.filter(visualization_id=self.visualization.visualization_id).count()

    def _get_cache(self, cache_key):

        cache=self.cache.get(cache_key)

        return cache

    def _set_cache(self, cache_key, value):

        return self.cache.set(cache_key, value, self.TTL)

    def count_by_day(self,day):
        """retorna los hits de un día determinado"""

        # si es datetime, usar solo date
        if type(day) == type(datetime.today()):
            day=day.date()

        cache_key="%s_hits_%s_by_date_%s" % ( self.doc_type, self.visualization.guid, str(day))

        hits = self._get_cache(cache_key)

        # si el día particular no esta en el caché, lo guarda
        # salvo que sea el parametro pasado sea de hoy, lo guarda en el cache pero usa siempre el de la DB
        if not hits or day == date.today():
            hits=VisualizationHits.objects.filter(visualization=self.visualization, created_at__startswith=day).count()

            self._set_cache(cache_key, hits)

        return (date,hits)

    def count_by_days(self, day=30, channel_type=None):
        """trae un dict con los hits totales de los ultimos day y los hits particulares de los días desde day hasta today"""

        # no sé si es necesario esto
        if day < 1:
            return {}

        cache_key="%s_hits_%s_%s" % ( self.doc_type, self.visualization.guid, day)

        if channel_type:
            cache_key+="_channel_type_%s" % channel_type

        hits = self._get_cache(cache_key)

        # me cachendié! no esta en la cache
        if not hits :
            # tenemos la fecha de inicio
            start_date=datetime.today()-timedelta(days=day)

            # tomamos solo la parte date
            truncate_date = connection.ops.date_trunc_sql('day', 'created_at')

            qs=VisualizationHits.objects.filter(visualization=self.visualization,created_at__gte=start_date)

            if channel_type:
                qs=qs.filter(channel_type=channel_type)

            hits=qs.extra(select={'_date': truncate_date, "fecha": 'DATE(created_at)'}).values("fecha").order_by("created_at").annotate(hits=Count("created_at"))

            control=[ date.today()-timedelta(days=x) for x in range(day-1,0,-1)]
            control.append(date.today())

            
            for i in hits:
                try:
                    control.remove(i['fecha'])
                except ValueError:
                    pass

            hits=list(hits)
                
            for i in control:
                hits.append({"fecha": i, "hits": 0})

            hits = sorted(hits, key=lambda k: k['fecha']) 

            # transformamos las fechas en isoformat
            hits=map(self._date_isoformat, hits)

            # lo dejamos, amablemente, en la cache!
            self._set_cache(cache_key, json.dumps(hits, cls=DjangoJSONEncoder))

            self.from_cache=False
        else:
            hits=json.loads(hits)
            self.from_cache=True

        return hits

    def _date_isoformat(self, row):
        row['fecha']=row['fecha'].isoformat()
        return row


class VisualizationSearchDAOFactory():
    """ select Search engine"""

    def __init__(self):
        pass

    def create(self, visualization_revision):
        if settings.USE_SEARCHINDEX == 'searchify':
            self.search_dao = VisualizationSearchifyDAO(visualization_revision)
        elif settings.USE_SEARCHINDEX == 'elasticsearch':
            self.search_dao = VisualizationElasticsearchDAO(visualization_revision)
        elif settings.USE_SEARCHINDEX == 'test':
            self.search_dao = VisualizationSearchDAO(visualization_revision)
        else:
            raise SearchIndexNotFoundException()

        return self.search_dao


class VisualizationSearchDAO():
    """ class for manage access to datasets' searchify documents """

    TYPE="vz"
    def __init__(self, visualization_revision):
        self.visualization_revision=visualization_revision
        self.search_index = SearchifyIndex()

    def _get_type(self):
        return self.TYPE
    def _get_id(self):
        """ Get Tags """
        return "%s::%s" %(self.TYPE.upper(),self.visualization_revision.visualization.guid)

    def _get_tags(self):
        """ Get Tags """
        return self.visualization_revision.tagvisualization_set.all().values_list('tag__name', flat=True)

    def _get_category(self):
        """ Get category name """
        #al final quedó cortito el método, eh!
        return self.visualization_revision.visualization.datastream.last_published_revision.category.categoryi18n_set.all()[0]

    def _get_i18n(self):
        """ Get category name """
        return VisualizationI18n.objects.get(visualization_revision=self.visualization_revision)
        
    def _build_document(self):

        tags = self._get_tags()

        category = self._get_category()
        visualizationi18n = self._get_i18n()

        text = [visualizationi18n.title, visualizationi18n.description, self.visualization_revision.user.nick, self.visualization_revision.visualization.guid]
        text.extend(tags) # visualization has a table for tags but seems unused. I define get_tags funcion for dataset.
        text = ' '.join(text)
        try:
            p = Preference.objects.get(account_id=self.visualization_revision.visualization.user.account_id, key='account.purpose')
            is_private = p.value == 'private'
        except Preference.DoesNotExist, e:
            is_private = False

        document = {
                'docid' : self._get_id(),
                'fields' :
                    {'type' : self.TYPE,
                     'visualization_id': self.visualization_revision.visualization.id,
                     'visualization_revision_id': self.visualization_revision.id,
                     'datastream_id': self.visualization_revision.visualization.datastream.id,
                     'title': visualizationi18n.title,
                     'text': text,
                     'description': visualizationi18n.description,
                     'owner_nick' :self.visualization_revision.user.nick,
                     'tags' : ','.join(tags),
                     'account_id' : self.visualization_revision.user.account.id,
                     'parameters': "",
                     'timestamp': int(time.mktime(self.visualization_revision.created_at.timetuple())),
                     'hits': 0,
                     'is_private': is_private and 1 or 0,
                    },
                'categories': {'id': unicode(category.category_id), 'name': category.name}
                }

        return document


class VisualizationSearchifyDAO(VisualizationSearchDAO):
    """ class for manage access to datasets' searchify documents """
    def __init__(self, visualization_revision):
        self.visualization_revision=visualization_revision
        self.search_index = SearchifyIndex()
        
    def add(self):
        self.search_index.indexit(self._build_document())
        
    def remove(self, visualization_revision):
        self.search_index.delete_documents([self._get_id()])


class VisualizationElasticsearchDAO(VisualizationSearchDAO):
    """ class for manage access to datasets' elasticsearch documents """

    def __init__(self, visualization_revision):
        self.visualization_revision=visualization_revision
        self.search_index = ElasticsearchIndex()
        
    def add(self):
        self.search_index.indexit(self._build_document())
        
    def remove(self):
        self.search_index.delete_documents([{"type": self._get_type(), "docid": self._get_id()}])
