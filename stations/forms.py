from django import forms
from .models import Stock, Station, Commune


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

class StationCreateForm(forms.ModelForm):
    """
    Formulaire permettant à un gérant de proposer une nouvelle station.
    La station devra ensuite être validée par un administrateur.
    """

    class Meta:
        model = Station
        fields = [
            "nom",
            "commune",
            "adresse",
            "latitude",
            "longitude",
        ]

        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom de la station",
            }),
            "commune": forms.Select(attrs={
                "class": "form-control",
            }),
            "adresse": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Adresse",
            }),
            "latitude": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "any",
            }),
            "longitude": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "any",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["commune"].queryset = Commune.objects.select_related(
            "cercle",
            "cercle__region"
        ).order_by(
            "cercle__region__nom",
            "cercle__nom",
            "nom",
        )

        self.fields["commune"].label_from_instance = (
            lambda obj: f"{obj.nom} ({obj.cercle.nom}, {obj.cercle.region.nom})"
        )