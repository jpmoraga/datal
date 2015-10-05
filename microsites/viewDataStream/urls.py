from django.conf.urls import *

urlpatterns = patterns('',
    url(r'^(?P<id>\d+)/(?P<slug>[A-Za-z0-9\-]+)/$', 'microsites.viewDataStream.views.view',
        name='viewDataStream.view'),
    url(r'^embed/(?P<guid>[A-Z0-9\-]+)$', 'microsites.viewDataStream.views.embed',
        name='viewDataStream.embed'),
    url(r'^(?P<id>\d+)-(?P<slug>[A-Za-z0-9\-]+).download$', 'microsites.viewDataStream.views.download',
        name='viewDataStream.download'),
    url(r'^get_last_30_days_datastream/(?P<id>\d+)$', 'microsites.viewDataStream.views.hits_stats',
        name='viewDataStream.get_last_30_days_datastream'),
    url(r'^category/(?P<category_slug>[A-Za-z0-9\-]+)/$', 'microsites.search.views.action_browse',
        name='search.action_browse'),
    url(r'^category/(?P<category_slug>[A-Za-z0-9\-]+)/page/(?P<page>\d+)/$', 'microsites.search.views.action_browse',
        name='search.action_browse'),
)
