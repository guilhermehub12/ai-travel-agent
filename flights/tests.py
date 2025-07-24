from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from .models import PriceAlert
import json

# Dados mockados da resposta do Amadeus (para não acabar com a cota free)
MOCK_AMADEUS_RESPONSE = {
    "data": [
        {
            "itineraries": [
                {
                    "segments": [
                        {
                            "departure": {"iataCode": "GRU", "at": "2025-10-25T08:00:00"},
                            "arrival": {"iataCode": "GIG", "at": "2025-10-25T09:00:00"},
                            "carrierCode": "G3",
                            "number": "1402"
                        }
                    ]
                }
            ],
            "price": {
                "total": "450.35"
            },
            "validatingAirlineCodes": ["G3"]
        }
    ],
    "dictionaries": {
        "carriers": {
            "G3": "GOL Linhas Aereas"
        }
    }
}


class FlightSearchViewTestCase(APITestCase):
    @patch('flights.views.search_flights_from_amadeus')
    def test_search_flights_success_with_mock(self, mock_amadeus_search):
        """
        Garante que a view processa corretamente a resposta mockada do Amadeus.
        """
        # Configuro o mock para retornar nossa resposta falsa quando for chamado.
        mock_sdk_response = MagicMock()
        mock_sdk_response.data = MOCK_AMADEUS_RESPONSE['data']
        mock_sdk_response.dictionaries = MOCK_AMADEUS_RESPONSE['dictionaries']

        mock_amadeus_search.return_value = mock_sdk_response

        url = reverse('search-flights')
        params = {'origem': 'GRU', 'destino': 'GIG', 'data': '2025-10-25'}

        response = self.client.get(url, params, format='json')
        # 1. O teste principal: a resposta da NOSSA API deve ser 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Verifica se nosso código parseou o preço corretamente
        self.assertEqual(response.data['opcoes_voo'][0]['preco'], "450.35")

        # 3. Verifica se nosso código encontrou o nome da companhia
        self.assertEqual(response.data['opcoes_voo']
                         [0]['companhia'], "GOL Linhas Aereas")

    def test_create_price_alert_success(self):
        """
        Garante que a view cria corretamente um alerta de preço.
        """
        url = reverse('create-alert')
        data = {
            'user_whatsapp_id': '5585999998888',
            'origin_code': 'GRU',
            'destination_code': 'GIG',
            'target_price': '400.00'
        }

        response = self.client.post(url, data, format='json')

        if response.status_code != status.HTTP_201_CREATED:
            print("Erro de validação retornado pela API:")
            print(json.dumps(response.data, indent=2))

        # Verifica se o alerta foi criado
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # verifica se o alerta foi salvo no bd
        self.assertTrue(
            PriceAlert.objects.filter(
                user_whatsapp_id="5585999998888",
                origin_code="GRU"
            ).exists()
        )
        # verifica a msg de sucesso
        self.assertEqual(response.data['mensagem'],
                         "Alerta criado com sucesso!")

    @patch('flights.views.search_flights_from_amadeus')
    def test_check_alerts_finds_cheaper_flight(self, mock_amadeus_search):
        """
        Garante que o 'check_alerts' encontra um voo mais barato e desativa o alerta.
        """
        # cria um alerta no bd de teste
        alert = PriceAlert.objects.create(
            user_whatsapp_id="5511988887777",
            origin_code="MAD",
            destination_code="BCN",
            target_price=500.00,
            is_active=True
        )

        # configura o mock para retornar um voo que custa menos que R$500
        mock_sdk_response = MagicMock()
        mock_sdk_response.data = MOCK_AMADEUS_RESPONSE['data']
        mock_sdk_response.dictionaries = MOCK_AMADEUS_RESPONSE['dictionaries']
        mock_amadeus_search.return_value = mock_sdk_response

        url = reverse('check-alerts')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # a resposta deve conter uma lista de usuários
        self.assertEqual(len(response.data['notifications_to_send']), 1)
        notification = response.data['notifications_to_send'][0]
        self.assertEqual(notification['user_whatsapp_id'], "5511988887777")
        self.assertEqual(notification['found_price'], "450.35")

        # o alerta no bd é desativado
        alert.refresh_from_db()
        self.assertFalse(alert.is_active)
