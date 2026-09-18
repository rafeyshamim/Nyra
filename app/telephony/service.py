from app.telephony.base import TelephonyProvider
from app.telephony.android_gateway import AndroidGatewayTelephonyProvider
from app.telephony.exotel import ExotelAgentStreamProvider
from app.config.settings import settings


class TelephonyService:
    """Factory selecting active telephony gateway."""

    @staticmethod
    def get_provider() -> TelephonyProvider:
        provider_type = settings.telephony_provider.lower()
        if provider_type == "exotel":
            return ExotelAgentStreamProvider()
        return AndroidGatewayTelephonyProvider()
