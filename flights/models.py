from django.db import models

class PriceAlert(models.Model):
    user_whatsapp_id = models.CharField(max_length=20)

    origin_code = models.CharField(max_length=3)
    destination_code = models.CharField(max_length=3)

    target_price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        status = "Ativo" if self.is_active else "Inativo"
        return f"Alerta de {self.origin_code} para {self.destination_code} por R${self.target_price} - ({status})"