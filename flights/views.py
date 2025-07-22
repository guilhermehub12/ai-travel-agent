from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class FlightSearchView(APIView):
    """
    View para buscar voos. Por enquanto, retorna dados fictícios.
    """
    def get(self, request, *args, **kwargs):
        # Captura os parâmetros da URI
        # ex: ?origem=SAO&destino=RIO&data=2025-10-25
        origem = request.query_params.get('origem', None)
        destino = request.query_params.get('destino', None)
        data = request.query_params.get('data', None)

        # Validação simples
        if not all([origem, destino, data]):
            return Response(
                {"erro": "Parâmetros 'origem', 'destino' e 'data' são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Dados mockados
        mock_flights = [
            {"voo": "GOL 1402", "companhia": "Gol", "horario": "06:30", "preco": "280.50"},
            {"voo": "LATAM 3340", "companhia": "Latam", "horario": "07:15", "preco": "320.00"},
            {"voo": "AZUL 4010", "companhia": "Azul", "horario": "08:20", "preco": "298.75"},
        ]

        # resposta final (json)
        response_data = {
            "rota": f"{origem} -> {destino}",
            "data": data,
            "opcoes_voo": mock_flights
        }

        return Response(response_data, status=status.HTTP_200_OK)