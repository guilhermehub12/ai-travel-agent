from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

class FlightSearchViewTestCase(APITestCase):
    def test_search_flights_success(self):
        """
        Garante que a busca de voos funciona com todos os parâmetros corretos.
        """
        # monta a URL dinamicamente
        url = reverse('search-flights')
        
        # Parâmetros da nossa requisição
        params = {'origem': 'SAO', 'destino': 'RIO', 'data': '2025-10-25'}

        # O client.get simula uma requisição GET para a URL com os parâmetros
        response = self.client.get(url, params)

        # Verifica se a resposta teve status 200
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verifica se 'opcoes_voo' (que possui as lista de viagens) está na resposta
        self.assertIn('opcoes_voo', response.data)
        
        # Verifica se a lista de voos não está vazia
        self.assertGreater(len(response.data['opcoes_voo']), 0)

    def test_search_flights_missing_params(self):
        """
        Garante que a API retorna um erro 400 se faltar um parâmetro.
        """
        url = reverse('search-flights')
        params = {'origem': 'SAO', 'destino': 'RIO'} # Faltando a 'data'

        response = self.client.get(url, params)

        # Verifica se a resposta foi um 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
