import openai
import os
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .amadeus_service import search_flights_from_amadeus
from datetime import datetime, date
from .serializers import PriceAlertSerializer
from .models import PriceAlert


def parse_amadeus_response(amadeus_response):
    """
    Função auxiliar para transformar a resposta complexa da Amadeus
    em uma lista simples que nossa API vai retornar.
    """
    flights_list = []

    carriers = amadeus_response.dictionaries.get(
        'carriers', {}) if amadeus_response.dictionaries else {}

    for offer in amadeus_response.data:
        price = offer.get('price', {}).get('total')

        try:
            # obtém o primeiro segmento do primeiro itinerário
            first_segment = offer.get('itineraries', [{}])[
                0].get('segments', [{}])[0]

            carrier_code = first_segment.get('carrierCode')
            flight_number = first_segment.get('number')
            departure_time = first_segment.get('departure', {}).get('at')

            flight_info = {
                "voo": f"{carrier_code} {flight_number}",
                "companhia": carriers.get(carrier_code, carrier_code),
                "horario": departure_time,
                "preco": price
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

        # Validação simples
        if not all([origem, destino, data]):
            return Response(
                {"erro": "Parâmetros 'origem', 'destino' e 'data' são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            search_date = datetime.strptime(data, '%Y-%m-%d').date()
            if search_date < date.today():
                return Response(
                    {"erro": "A data da busca não pode ser no passado."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {"erro": "Formato de data inválido. Use AAAA-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )
        print("origem: ", origem, "destino: ", destino, "data: ", data)
        amadeus_response = search_flights_from_amadeus(origem, destino, data)
        print("amadeus_response 1 :", amadeus_response)

        if not amadeus_response:
            return Response(
                {"mensagem": "Nenhum voo encontrado ou erro na consulta à Amadeus."},
                status=status.HTTP_404_NOT_FOUND
            )
        print("amadeus_response 2 :", amadeus_response)
        # formatação dos dados
        parsed_flights = parse_amadeus_response(amadeus_response)
        print("parsed :", parsed_flights)

        response_data = {
            "rota": f"{origem} -> {destino}",
            "data": data,
            "opcoes_voo": parsed_flights
        }

        return Response(response_data, status=status.HTTP_200_OK)


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


class OpenAIUnderstandView(APIView):
    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message', '')
        if not user_message:
            return Response({"error": "Mensagem não fornecida"}, status=status.HTTP_400_BAD_REQUEST)

        openai.api_key = os.getenv('OPENAI_API_KEY')
        client = openai.OpenAI()

        prompt_template = """
            Você é um assistente NLU (Natural Language Understanding) para um chatbot de agência de viagens chamado "milha.ai". Sua tarefa é analisar a mensagem do usuário e extrair a "intenção" (intent) e as "entidades" (entities) relevantes, retornando-os em um formato JSON estrito.

            A data de hoje é: {current_date}. Use esta data como referência para resolver datas relativas como "amanhã" ou "próxima sexta-feira".

            As intenções (intent) possíveis são: "search_flight", "create_alert", "greeting", "help", "unknown".
            As entidades (entities) possíveis são: "origin", "destination", "departure_date" (formato AAAA-MM-DD), "target_price" (número).

            Regras:
            1. Se uma entidade não for mencionada, seu valor deve ser null.
            2. Responda APENAS com o objeto JSON. Não adicione explicações ou texto extra.

            Analise a seguinte mensagem do usuário:
        """

        final_prompt = prompt_template.format(
            current_date=date.today().strftime('%Y-%m-%d'))

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=[
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"}
            )

            ai_json_response = json.loads(response.choices[0].message.content)
            return Response(ai_json_response, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Não foi possível processar a mensagem: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
