from django import forms
from .models import Stock


class StockForm(forms.ModelForm):
    """
    Formulaire utilisé dans le dashboard gérant pour mettre à jour le stock.

    - La station n’est PAS demandée ici (ajoutée dans la vue).
    - On s'appuie sur les choices du modèle pour éviter les conflits.
    """

    class Meta:
        model = Stock
        fields = ["produit", "niveau"]
        widgets = {
            "produit": forms.Select(attrs={"class": "form-control"}),
            "niveau": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # PRODUIT : partir des choices du modèle
        produit_field = Stock._meta.get_field("produit")
        base_prod_choices = list(produit_field.choices)

        cleaned_prod_choices = []
        for value, label in base_prod_choices:
            # si jamais "petrole" existe encore dans les choices, on le supprime
            if value == "petrole":
                continue
            # on renomme l'affichage de super en Essence
            if value == "super":
                label = "Essence"
            cleaned_prod_choices.append((value, label))

        self.fields["produit"].choices = cleaned_prod_choices

        # NIVEAU : on garde les mêmes choices que dans le modèle
        niveau_field = Stock._meta.get_field("niveau")
        self.fields["niveau"].choices = list(niveau_field.choices)
