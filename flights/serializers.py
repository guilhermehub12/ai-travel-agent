from rest_framework import serializers
from .models import PriceAlert


class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        fields = ['user_whatsapp_id', 'origin_code',
                  'destination_code', 'target_price']
