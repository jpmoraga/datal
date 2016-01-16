import re
import logging

from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from django.template import TemplateDoesNotExist
from django.views.generic import TemplateView

from core.models import *
from core.daos.datastreams import DataStreamDBDAO
from core.daos.visualizations import VisualizationDBDAO
from core.choices import StatusChoices
from core.http import get_domain_by_request
from core.shortcuts import render_to_response


def custom_pages(request, page):
    try:
        preferences = request.account.get_preferences()
        url = preferences['account_url']
        cv = CustomView.as_view(template_name="custom/{0}/{1}.html".format(url, page), extra_content=locals())
        return cv(request)
    except TemplateDoesNotExist:
        raise Http404()


def get_css(request, url_name, id):
    key = get_key(url_name)
    try:
        css = Preference.objects.get_value_by_account_id_and_key(id, '%s.css' % key)
    except Preference.DoesNotExist:
        css = ''
    return HttpResponse(css, content_type='text/css')

def get_js(request, url_name, id):
    key = get_key(url_name)
    try:
        javascript = Preference.objects.get_value_by_account_id_and_key(id, '%s.javascript' % key)
    except Preference.DoesNotExist:
        javascript = ''
    return HttpResponse(javascript, content_type='text/javascript')


def get_key(url_name):
    logger = logging.getLogger(__name__)
    
    if not url_name:
        logger.error('No url_name')
        raise Http404

    #TODO encontrar la forma de llevar esto al plugin en ds.detail y en chart.detail hay cosas de plugins.
    if url_name in ['viewDataStream.view', 'viewCustomViews.customviews_list', 'viewCustomViews.save', 'viewCustomViews.view']:
        key = 'ds.detail'
    elif url_name in ['viewDataStream.embed']:
        key = 'ds.embed'
    #elif re.search('^.*/(datastreams|dataviews)/\d+/[A-Za-z0-9\-]+$' , http_referer):
    #    key = 'ds.detail'
    elif url_name in ['search.search_by_query_and_category', 'search.search', 'search.browse']:
        key = 'search'
    elif url_name in ['chart_manager.embed', 'viewChart.embed']:
        key = 'chart.embed'
    elif url_name in ['loadHome.load', 'loadHome.update_list', 'loadHome.update_categories']:
        key = 'home'
    elif url_name in ['manageDeveloper.filter']:
        key = 'developers'
    elif url_name in ['chart_manager.view', 'viewCustomViz.list', 'viewCustomViz.save', 'viewCustomViz.view']:
        key = 'chart.detail'
    #elif re.search('^.*/visualizations/\d+/[A-Za-z0-9\-]+/.*$' , http_referer):
    #    key = 'chart.detail'
    elif url_name in ['viewDashboards.view']:
        key = 'db.detail'
    elif url_name in ['manageDatasets.view']:
        key = 'dataset'
    else:
        #  http referer error http://microsites.dev:8080/dataviews/69620/iep-primer-trimestre-2012-ministerio-de-defensa-nacional
        logger.error('Url_name sin macheo %s' % url_name)
        raise Http404

    return key + '.full'


def get_new_css(request, url_name, id):
    try:
        account = request.account
        preferences = account.get_preferences()
        keys = [
            'account.title.color',
            'account.button.bg.color',
            'account.button.border.color',
            'account.button.font.color',
            'account.mouseover.bg.color',
            'account.mouseover.border.color',
            'account.mouseover.title.color',
            'account.mouseover.text.color'
        ]
        keys_copy = list(keys)
        preferences.load(keys)

        for key in keys_copy:
            if preferences[key.replace('.', '_')]:
                return render_to_response('css_branding/branding.css', locals(), mimetype = 'text/css')

        # Joaco!, remove when the branding migration ...
        default_chart_css = '.chartBox .chartTitle a:hover{background:#ccc !important;} .chartBox .chartTitle a:hover{border-color:#999 !important;} .chartBox .chartTitle a:hover{color:#fff !important;}'
        return HttpResponse(default_chart_css, content_type='text/css')
    except AttributeError:
        return HttpResponse('', content_type='text/css')


def is_live(request):
    callback = request.GET.get('callback')
    response = '%s(true)' % callback
    return HttpResponse(response, content_type='text/javascript')


def get_catalog_xml(request):
    logger = logging.getLogger(__name__)

    account_id = request.account.id
    language = request.auth_manager.language
    preferences = request.preferences
    account = request.account
    
    domain = get_domain_by_request(request)
    api_domain = preferences['account_api_domain']
    transparency_domain = preferences['account_api_transparency']
    account = Account.objects.get(pk=account_id)
    msprotocol = 'https' if account.get_preference('account.microsite.https') else 'http'
    apiprotocol = 'https' if account.get_preference('account.api.https') else 'http'
    developers_link = msprotocol + '://' + domain + reverse('manageDeveloper.filter')
    datastreams_revision_ids = DataStreamRevision.objects.values_list('id').filter(
        datastream__user__account_id=account_id, status=StatusChoices.PUBLISHED
    )
    resources = []
    for datastream_revision_id, in datastreams_revision_ids:
        try:
            ds = DataStreamDBDAO().get(language, datastream_revision_id=datastream_revision_id)
        except:
            logger.error('catalog ERROR %s %s' % (datastream_revision_id, language))
            continue

        ds.link = '{}://{}{}'.format(msprotocol, domain, ds.permalink())
        ds.export_csv_link = '{}://{}{}'.format(msprotocol, domain,reverse('viewDataStream.csv', kwargs={'id': ds.datastream_id, 'slug': ds.slug}))
        ds.export_html_link = '{}://{}{}'.format(msprotocol, domain, reverse('viewDataStream.html', kwargs={'id': ds.datastream_id, 'slug': ds.slug}) )
        ds.api_link = apiprotocol + '://' + api_domain + '/datastreams/' + ds.guid + '/data/?auth_key=your_authkey'

        ds.visualizations = []
        visualization_revision_ids = VisualizationRevision.objects.values_list('id').filter(
            visualization__datastream_id=ds.datastream_id,
            status=StatusChoices.PUBLISHED
        )
        for visualization_revision_id, in visualization_revision_ids:
            try:
                vz = VisualizationDBDAO().get(language, visualization_revision_id=visualization_revision_id)
            except:
                logger.error('catalog VIZ ERROR %s %s' % (visualization_revision_id, language))
                continue
            vz['link'] = msprotocol + '://' + domain + vz.permalink()
            ds.visualizations.append(vz)
        resources.append(ds)

    return render_to_response('catalog.xml', locals(), mimetype='application/xml')


class CustomView(TemplateView):

    extra_content = {}

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)
        context.update(self.extra_content)
        return context
