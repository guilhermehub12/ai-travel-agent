from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch

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
        mock_amadeus_search.return_value = MOCK_AMADEUS_RESPONSE
        
        url = reverse('search-flights')
        params = {'origem': 'GRU', 'destino': 'GIG', 'data': '2025-10-25'}

        response = self.client.get(url, params)

        # 1. O teste principal: a resposta da NOSSA API deve ser 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Verifica se nosso código parseou o preço corretamente
        self.assertEqual(response.data['opcoes_voo'][0]['preco'], "450.35")
        
        # 3. Verifica se nosso código encontrou o nome da companhia
        self.assertEqual(response.data['opcoes_voo'][0]['companhia'], "GOL Linhas Aereas")

