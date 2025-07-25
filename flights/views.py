import openai
import os
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .amadeus_service import search_flights_from_amadeus
from datetime import datetime, date, timedelta
from .serializers import PriceAlertSerializer
from .models import PriceAlert
from amadeus import ResponseError
from django.views.generic import ListView

def parse_amadeus_response(amadeus_response):
    """
    Função auxiliar para transformar a resposta complexa da Amadeus
    em uma lista simples que nossa API vai retornar.
    """
    flights_list = []

    carriers = {}

    if hasattr(amadeus_response, 'dictionaries') and amadeus_response.dictionaries is not None:
        carriers = amadeus_response.dictionaries.get('carriers', {})

    for offer in amadeus_response.data:
        try:
            # Pega o primeiro itinerário da oferta (geralmente o voo de ida)
            itinerary = offer['itineraries'][0]
            segments = itinerary['segments']

            # obtém o primeiro e o último trecho da viagem
            first_segment = segments[0]
            last_segment = segments[-1]

            # Calcula o número de paradas
            stops = len(segments) - 1

            carrier_code = first_segment['carrierCode']

            flight_info = {
                "origin": first_segment['departure']['iataCode'],
                "destination": last_segment['arrival']['iataCode'],
                "departure_time": first_segment['departure']['at'],
                "arrival_time": last_segment['arrival']['at'],
                "stops": stops,
                "duration": itinerary['duration'],
                "carrier": carriers.get(carrier_code, carrier_code),
                "price": offer.get('price', {}).get('total')
            }
            flights_list.append(flight_info)

        except (IndexError, KeyError) as e:
            print(f"Erro ao processar uma oferta de voo: {e}")
            continue
    return flights_list


class FlightSearchView(APIView):
    """
    View para buscar voos.
    """

    def get(self, request, *args, **kwargs):
        origem = request.query_params.get('origem', None)
        destino = request.query_params.get('destino', None)
        data = request.query_params.get('data', None)
        print("origem: ", origem)
        # Validação simples
        if not all([origem, destino, data]):
            return Response(
                {"erro": "Parâmetros 'origem', 'destino' e 'data' são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            search_date_obj = datetime.strptime(data, '%Y-%m-%d').date()

            if search_date_obj < date.today():
                return Response(
                    {"erro": "A data da busca não pode ser no passado."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {"erro": "Formato de data inválido. Use AAAA-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amadeus_response = search_flights_from_amadeus(
                origem, destino, data)

            if not amadeus_response or not amadeus_response.data:
                return Response({"mensagem": "Nenhum voo encontrado para esta rota e data."},
                                status=status.HTTP_404_NOT_FOUND)

            parsed_flights = parse_amadeus_response(amadeus_response)

            response_data = {
                "route": f"{origem} -> {destino}",
                "date": data,
                "flight_options": parsed_flights
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ResponseError as e:
            error_details = e.response.result if hasattr(
                e, 'response') and hasattr(e.response, 'result') else str(e)
            return Response(
                {"erro": "Falha ao consultar a API da Amadeus.",
                    "detalhes": error_details},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {"erro": "Ocorreu um erro interno inesperado no servidor.",
                    "detalhes": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PriceAlertCreateView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = PriceAlertSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"mensagem": "Alerta criado com sucesso!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckAlertsView(APIView):
    def get(self, request, *args, **kwargs):
        active_alerts = PriceAlert.objects.filter(is_active=True)
        notifications_to_send = []

        # A data da busca será sempre o dia de amanhã para garantir voos
        search_date = date.today().replace(day=date.today().day + 1).strftime('%Y-%m-%d')

        for alert in active_alerts:
            print(
                f"Verificando alerta para {alert.origin_code} -> {alert.destination_code}")

            amadeus_response = search_flights_from_amadeus(
                alert.origin_code,
                alert.destination_code,
                search_date
            )

            if not amadeus_response or not amadeus_response.data:
                continue  # Pula para o próximo alerta se não encontrar voos

            # Encontra o voo mais barato na resposta
            from decimal import Decimal
            cheapest_flight_price = min(
                [Decimal(offer['price']['total'])
                 for offer in amadeus_response.data]
            )

            if cheapest_flight_price <= alert.target_price:
                print(
                    f"PREÇO BOM ENCONTRADO! Alvo: {alert.target_price}, Encontrado: {cheapest_flight_price}")

                # Adiciona à lista de notificações
                notifications_to_send.append({
                    'user_whatsapp_id': alert.user_whatsapp_id,
                    'origin': alert.origin_code,
                    'destination': alert.destination_code,
                    'target_price': str(alert.target_price),
                    'found_price': str(cheapest_flight_price)
                })

                # Desativa o alerta para não notificar de novo
                alert.is_active = False
                alert.save()

        return Response({"notifications_to_send": notifications_to_send}, status=status.HTTP_200_OK)

class AlertsDashboardView(ListView):
    model = PriceAlert
    template_name = 'flights/dashboard.html'
    context_object_name = 'alerts'

    def get_queryset(self):
        return PriceAlert.objects.filter(is_active=True).order_by('-created_at')

