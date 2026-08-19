# V1.1-L — Lot 7 — Documents Cloud dans l'application Windows

## Fonctionnalités ajoutées

- Connexion de la page **Documents** aux routes Cloud déjà déployées.
- Génération sécurisée de la **Convention**, du **Programme** et de la **Convocation**.
- Option A : le commercial sélectionne son prospect et la formation, puis renseigne les dates, horaires, modalité, participants, formateur, financeur et lien de connexion.
- Le tarif n'est jamais saisi par le commercial : il est repris du catalogue Cloud par le serveur.
- Historique des documents visibles selon les droits du compte.
- Téléchargement local par lien Supabase privé temporaire.
- Dépôt administrateur des **Devis**, **Factures** et **Attestations de formation**.
- Création initiale d'une formation Cloud par l'administrateur.
- Upload administrateur des modèles DOCX officiels pour Convention, Programme et Convocation.
- Conservation complète du moteur documentaire SQLite local.

## Sécurité

- Les prospects proposés proviennent exclusivement de l'API et respectent la visibilité serveur.
- L'application ne reçoit jamais la clé Supabase service-role.
- Les uploads utilisent les routes administrateur protégées.
- Les téléchargements utilisent des URL signées temporaires.
