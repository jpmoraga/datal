from core.models import DataStreamHits, VisualizationHits, DashboardHits
import logging

def create_report(object_id, model, channel_type):
    logger = logging.getLogger(__name__)

    logger.info("estamos usando create_report para hittear, por favor cambiar por core.daos.{DataStream/Visualization}HitsDao")
    if model == DataStreamHits:
        model.objects.create(datastream_id=object_id, channel_type=channel_type)
    elif model == VisualizationHits:
         model.objects.create(visualization_id=object_id, channel_type=channel_type)
    elif model == DashboardHits:
         model.objects.create(dashboard_id=object_id, channel_type=channel_type)
