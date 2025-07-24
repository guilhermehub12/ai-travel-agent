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


class OpenAIUnderstandView(APIView):
    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message', '')
        print(user_message)
        if not user_message:
            return Response({"error": "Mensagem não fornecida"}, status=status.HTTP_400_BAD_REQUEST)

        openai.api_key = os.getenv('OPENAI_API_KEY')
        client = openai.OpenAI()

        prompt_template = """
            Você é um assistente NLU (Natural Language Understanding) para um chatbot de agência de viagens chamado "milha.ai". Sua tarefa é analisar a mensagem do usuário e extrair a "intenção" (intent) e as "entidades" (entities) relevantes, retornando-os em um formato JSON estrito.

            A data de hoje é: {current_date}. Use esta data como referência para resolver datas relativas como "amanhã", "próxima sexta-feira", "dia 20 de setembro", etc.

            As intenções (intent) possíveis são:
            - "search_flight": O usuário quer pesquisar um voo.
            - "create_alert": O usuário quer criar um alerta de preço.
            - "greeting": O usuário está apenas cumprimentando.
            - "help": O usuário está pedindo ajuda.
            - "unknown": A intenção não se encaixa em nenhuma das anteriores.

            As entidades (entities) possíveis são:
            - "origin": A cidade ou aeroporto de origem.
            - "destination": A cidade ou aeroporto de destino.
            - "departure_date": A data da viagem, sempre no formato AAAA-MM-DD.
            - "target_price": O preço alvo para um alerta, como um número.

            Regras:
            1. Se uma entidade não for mencionada na mensagem, seu valor no JSON deve ser null.
            2. Seja preciso na extração. "SP" ou "São Paulo" devem ser tratados como a mesma origem.
            3. Para datas relativas, calcule a data exata com base na data de hoje fornecida.
            4. Responda APENAS com o objeto JSON. Não adicione nenhuma explicação, introdução ou texto adicional.
            5. Transformar o nome da cidade para símbolo (exemplo: Fortaleza será igual a FOR e assim por diante)

            --- EXCEPCIONALMENTE AQUI, ALGUNS EXEMPLOS DE COMO VOCÊ DEVE SE COMPORTAR: ---

            Mensagem: "Oi, tudo bem?"
            JSON:
            
            "intent": "greeting",
            "entities": 
                "origin": null,
                "destination": null,
                "departure_date": null,
                "target_price": null

            Mensagem: "Quero uma passagem de Fortaleza para Guarulhos na próxima quarta-feira"
            JSON:
            
            "intent": "search_flight",
            "entities": 
                "origin": "FOR",
                "destination": "GRU",
                "departure_date": "2025-07-30",
                "target_price": null

            Mensagem: "me avise quando o voo pra salvador ficar abaixo de 500 reais"
            JSON:
            
            "intent": "create_alert",
            "entities": 
                "origin": null,
                "destination": "SSA",
                "departure_date": null,
                "target_price": 500
            --- FIM DOS EXEMPLOS ---

            Agora, analise a seguinte mensagem do usuário:
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
