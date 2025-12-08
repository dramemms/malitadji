from django import forms
from .models import Stock


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        # On ne demande PAS la station ici, on la déduit dans la vue
        fields = ["produit", "niveau"]
        widgets = {
            "produit": forms.Select(attrs={"class": "form-control"}),
            "niveau": forms.Select(attrs={"class": "form-control"}),
        }
