# stations/signals.py
"""
DÉSACTIVÉ (architecture finale Malitadji)

Raison:
- La source de vérité = /manager/ (gérant)
- Le push FCM + InApp doivent être déclenchés UNIQUEMENT depuis manager_dashboard()
  pour contrôler old_niveau -> new_niveau et éviter doublons / surprises.
"""

# Tu peux laisser ce fichier vide.
def ready(self):
    import stations.signals
