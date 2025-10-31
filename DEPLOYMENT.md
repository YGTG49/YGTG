# Déploiement de la plateforme d'envoi d'e-mails

Ce document décrit comment préparer l'environnement, configurer le pool SMTP et lancer l'API FastAPI ainsi que le frontend statique.

## 1. Pré-requis

- Python 3.10 ou supérieur
- Un serveur SMTP accessible (Mailgun, Sendgrid, Postmark, serveur interne, etc.)
- `bash` pour exécuter le script `scripts/start.sh`
- (Optionnel) Un serveur HTTP pour exposer le fichier `index.html` (par exemple Nginx, Vercel ou GitHub Pages)

## 2. Variables d'environnement

Les variables ci-dessous contrôlent le pool SMTP et le rate limit :

| Variable | Description | Défaut |
| --- | --- | --- |
| `SMTP_HOST` | Nom d'hôte ou IP du serveur SMTP | `localhost` |
| `SMTP_PORT` | Port SMTP | `1025` |
| `SMTP_USERNAME` | Nom d'utilisateur SMTP | `None` |
| `SMTP_PASSWORD` | Mot de passe SMTP | `None` |
| `SMTP_USE_TLS` | Activer STARTTLS (`true`/`false`) | `false` |
| `SMTP_POOL_SIZE` | Nombre max de connexions simultanées | `5` |
| `SMTP_TIMEOUT` | Délai de connexion en secondes | `30` |
| `RATE_LIMIT_COUNT` | Nombre d'e-mails maximum par période | `30` |
| `RATE_LIMIT_PERIOD` | Durée de la période (secondes) | `60` |
| `DEFAULT_SENDER` | Adresse e-mail utilisée si le formulaire n'en fournit pas | `None` |

Exportez ces variables avant de démarrer l'application :

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USERNAME=apikey
export SMTP_PASSWORD="secret"
export SMTP_USE_TLS=true
export DEFAULT_SENDER="support@example.com"
```

## 3. Lancement local

1. Ouvrez un terminal à la racine du projet
2. Rendez le script exécutable (une fois) :
   ```bash
   chmod +x scripts/start.sh
   ```
3. Démarrez l'API :
   ```bash
   scripts/start.sh
   ```
   Le serveur FastAPI écoute par défaut sur `http://127.0.0.1:8000`.
4. Ouvrez `index.html` dans un navigateur ou servez le fichier via un serveur statique.

## 4. Déploiement de production

1. **Backend**
   - Créez un service systemd ou un conteneur Docker qui exécute `scripts/start.sh`
   - Configurez les variables d'environnement via votre orchestrateur (systemd `EnvironmentFile`, variables Docker, secrets Kubernetes, etc.)
   - Placez un reverse proxy (Nginx, Traefik, Cloudflare) devant l'API et forcez TLS.
   - Exposez uniquement les routes `/send` et `/health` si nécessaire.

2. **Frontend**
   - Hébergez `index.html` sur un CDN ou serveur statique.
   - Si le frontend est servi depuis un autre domaine, configurez `fetch('https://api.example.com/send')` dans le JavaScript (ou configurez `BASE_API_URL` via variable globale).
   - Ajoutez les en-têtes CORS au niveau du proxy si vous restreignez les origines.

3. **Supervision**
   - Surveillez les logs pour repérer les envois bloqués (liste `skipped`).
   - Utilisez la route `GET /health` pour les checks de disponibilité.
   - Ajustez `RATE_LIMIT_COUNT` et `RATE_LIMIT_PERIOD` en fonction des règles de votre fournisseur SMTP.

## 5. Tests manuels

- Lancer un serveur SMTP de test : `python -m aiosmtpd -n -l localhost:1025`
- Tester l'API :
  ```bash
  curl -X POST http://127.0.0.1:8000/send \
    -F "subject=Hello" \
    -F "sender=team@example.com" \
    -F "template_name=test" \
    -F "template_body=<p>Salut ${prenom}</p>" \
    -F "csv_file=@contacts.csv"
  ```
- Le fichier CSV doit contenir au moins une colonne `email` et optionnellement `prenom`, `entreprise`, etc.

## 6. Sécurité

- Stockez `SMTP_PASSWORD` dans un gestionnaire de secrets.
- Activez TLS côté SMTP en définissant `SMTP_USE_TLS=true`.
- Ajoutez un mécanisme d'authentification (clé API, JWT) au proxy ou directement dans FastAPI si l'API est exposée publiquement.
