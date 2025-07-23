import os
from dotenv import load_dotenv
from amadeus import Client, ResponseError

load_dotenv()

AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
AMADEUS_HOSTNAME = os.getenv('AMADEUS_HOSTNAME')

amadeus = Client(
    client_id=AMADEUS_API_KEY,
    client_secret=AMADEUS_API_SECRET,
    hostname=AMADEUS_HOSTNAME | 'test'
)


def search_flights_from_amadeus(origin, destination, date):
    """
    Busca voos na Amadeus usando um token de acesso.
    """
    try:
        params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': date,
            'adults': 1,
            'currencyCode': 'BRL',
            'max': 1
        }

        response = amadeus.shopping.flight_offers_search.get(**params) 
        print("response: ", response)
        return response

    except ResponseError as error:
        print(f"Erro ao chamar a API da Amadeus com o SDK: {error}")
        print(error.response.result)
        return None
