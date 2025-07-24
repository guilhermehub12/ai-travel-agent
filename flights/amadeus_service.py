import os
import json
from dotenv import load_dotenv
from amadeus import Client, ResponseError
from unittest.mock import MagicMock

load_dotenv()

AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
AMADEUS_HOSTNAME = os.getenv('AMADEUS_HOSTNAME', 'test')

USE_MOCK_AMADEUS = os.getenv('USE_MOCK_AMADEUS') == 'True'

print(f"--- CONECTANDO AO AMADEUS EM AMBIENTE: {AMADEUS_HOSTNAME.upper()} ---")

def _get_mock_flights(origin, destination, date):
    """Função interna para carregar e retornar dados do nosso arquivo mockado (JSON)."""
    print("--- USANDO DADOS MOCKADOS (OFFLINE) ---")
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mock_file_path = os.path.join(base_dir, 'mock_flight_data.json')

        # Abre o arquivo de dados fictícios
        with open(mock_file_path, 'r') as f:
            all_mock_data = json.load(f)

        # Cria uma chave de rota para procurar no JSON (ex: "MAD-BCN-2025-11-20")
        route_key = f"{origin}-{destination}-{date}"

        route_data = all_mock_data.get(route_key)

        if not route_data:
            print(f"Rota {route_key} não encontrada no arquivo mock.")
            return None

        # objeto mock que se parece com a resposta real do SDK
        mock_sdk_response = MagicMock()
        mock_sdk_response.data = route_data.get('data', [])
        mock_sdk_response.dictionaries = route_data.get('dictionaries', {})

        return mock_sdk_response

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Erro ao ler o arquivo de mock: {e}")
        return None


def search_flights_from_amadeus(origin, destination, date):
    """
    Busca voos na Amadeus usando um token de acesso.
    """
    if USE_MOCK_AMADEUS:
        return _get_mock_flights(origin, destination, date)
    else:
        try:
            amadeus = Client(
                client_id=AMADEUS_API_KEY,
                client_secret=AMADEUS_API_SECRET,
                hostname=AMADEUS_HOSTNAME
            )
            
            print(f"Buscando voos: {origin}->{destination} em {date}")
            params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': date,
                'adults': 1,
                'max': 5
            }

            response = amadeus.shopping.flight_offers_search.get(**params)
            print("response: ", response)
            return response

        except ResponseError as error:
            print(f"Erro ao chamar a API da Amadeus com o SDK: {error}")
            print(error.response.result)
            raise error
