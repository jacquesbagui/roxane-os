# Roxane OS

<div align="center">

```
   ██████╗  ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗███████╗
   ██╔══██╗██╔═══██╗╚██╗██╔╝██╔══██╗████╗  ██║██╔════╝
   ██████╔╝██║   ██║ ╚███╔╝ ███████║██╔██╗ ██║█████╗
   ██╔══██╗██║   ██║ ██╔██╗ ██╔══██║██║╚██╗██║██╔══╝
   ██║  ██║╚██████╔╝██╔╝ ██╗██║  ██║██║ ╚████║███████╗
   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝
```

**Système d'exploitation IA personnalisé pour assistant personnel**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jacquesbagui/roxane-os)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-orange.svg)](https://ubuntu.com)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)

[Installation](#-installation-rapide) • [Documentation](#-documentation) • [Fonctionnalités](#-fonctionnalités) • [Architecture](#-architecture)

</div>

---

## 📖 Qu'est-ce que Roxane OS ?

**Roxane OS** est un système d'exploitation Linux personnalisé basé sur **Ubuntu**, conçu pour offrir un assistant personnel IA intelligent, autonome et entièrement contrôlable. Roxane fonctionne **100% en local** avec un contrôle total sur vos données et le comportement du système.

### 🎯 Objectif Principal

Créer un assistant IA personnel capable d'interagir naturellement en français, d'effectuer des recherches autonomes, de contrôler le système d'exploitation, et d'apprendre continuellement.

---

## ✨ Fonctionnalités

### 🗣️ Communication Naturelle
- **Vocal** : Parlez à Roxane naturellement en français
- **Textuel** : Interface chat avec historique contextuel
- **STT** : Whisper Large v3 (précision > 95%)
- **TTS** : Coqui XTTS v2 avec voix personnalisée
- **VAD** : Détection automatique de la parole (Silero)

### 🧠 Intelligence Artificielle
- **LLM** : LLaMA 3.1 70B (ou TinyLlama 1.1B en dev)
- **Fine-tuning** : LoRA adaptatifs pour personnalisation continue
- **NLP** : Classification d'intentions, extraction d'entités, gestion du contexte
- **Mémoire** : Système de mémoire à court et long terme
- **Apprentissage** : Fine-tuning automatique hebdomadaire

### 🌐 Recherche et Navigation Web
- **Recherche autonome** : Métamoteur privé (SearxNG)
- **Scraping intelligent** : Extraction de données avec Playwright
- **Synthèse** : Résumés multi-sources automatiques
- **Navigation** : Browser intégré avec automation complète
- **Extraction** : Données structurées (tableaux, formulaires)

### 💻 Contrôle Système Complet
- **Applications** : Ouverture, fermeture, gestion de fenêtres
- **Fichiers** : CRUD complet, recherche, organisation automatique
- **Commandes** : Exécution bash avec sandbox Docker
- **Monitoring** : CPU, GPU, RAM, température, processus
- **Packages** : Installation apt/snap/flatpak avec confirmation

### 🎨 Interface Moderne
- **PyQt6** : Interface graphique native performante
- **Terminal intégré** : Avec historique et coloration syntaxique
- **Browser intégré** : Navigation web avec surlignage des extractions
- **Panneau d'activité** : Suivi en temps réel des actions
- **Thèmes** : Sombre/Clair avec personnalisation complète

### 🔒 Sécurité et Confidentialité
- **100% Local** : Aucune donnée envoyée dans le cloud
- **Sandbox Docker** : Isolation de l'exécution de code
- **Permissions** : 5 niveaux granulaires (0-4)
- **Audit** : Logs complets de toutes les actions
- **RGPD** : Droit à l'effacement, export de données
- **Chiffrement** : Base de données et backups (optionnel)

---

## 🔧 Prérequis

### Configuration Minimale (VM / Développement)

```
OS       : Ubuntu Server 25.10 LTS
CPU      : 4 cores
RAM      : 8 GB
Disque   : 50 GB
GPU      : Optionnel (CPU en dev)
```

### Configuration Recommandée (Production avec GPU)

```
OS       : Ubuntu Server 25.10 LTS
CPU      : AMD Ryzen 9 7950X ou Intel i9-13900K
RAM      : 64 GB DDR5
GPU      : NVIDIA RTX 4090 24GB (ou 2x RTX 3090)
VRAM     : 24 GB minimum
Disque   : 200 GB NVMe SSD
PSU      : 1000W
```

---

## 🚀 Installation Rapide

### Option 1 : Installation Automatique (Recommandée)

```bash
# Sur Ubuntu 24.04 fraîchement installé
curl -fsSL https://raw.githubusercontent.com/jacquesbagui/roxane-os/main/quick-install.sh | sudo bash
```

⏱️ **Durée** : 20-30 minutes  
✨ **Résultat** : Roxane OS prêt à l'emploi après reboot

### Option 2 : Installation Manuelle

```bash
# 1. Cloner le repository
git clone https://github.com/jacquesbagui/roxane-os.git
cd roxane-os

# 2. Rendre les scripts exécutables
chmod +x install-roxane-os.sh
chmod +x scripts/*.sh

# 3. Installer les dépendances de base
sudo ./setup-initial.sh

# 4. Redémarrer la session
exit
# Reconnectez-vous via SSH

# 5. Installer Roxane OS complet
sudo ./install-roxane-os.sh

# 6. Après le reboot automatique
roxane-start
```

---

## 🎮 Utilisation

### Commandes Principales

```bash
# Démarrer Roxane
roxane-start

# Arrêter Roxane
roxane-stop

# Redémarrer
roxane-restart

# Vérifier le statut
roxane-status

# Consulter les logs en temps réel
roxane-logs

# Mettre à jour
roxane-update

# Créer une sauvegarde
roxane-backup

# Ouvrir la configuration
roxane-config
```

### Exemples d'Interactions

#### Mode Vocal
```
Utilisateur : "Roxane, recherche les dernières actualités sur l'IA"
Roxane : "Je lance une recherche web..."
         [Affiche résultats synthétisés avec sources]

Utilisateur : "Ouvre VSCode"
Roxane : "J'ouvre Visual Studio Code"
         [Lance l'application]

Utilisateur : "Quelle est la température de mon GPU ?"
Roxane : "Votre GPU est à 68°C, utilisation 45%"
```

#### API REST

```bash
# Envoyer un message via l'API
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Trouve tous mes fichiers Python modifiés aujourd'hui"
  }'
```

#### Python SDK

```python
from core.engine import RoxaneEngine

# Initialiser Roxane
roxane = RoxaneEngine()

# Envoyer une requête
response = await roxane.process_message(
    "Crée un script qui renomme tous mes .txt en .md"
)
print(response.text)
print(response.actions)  # Actions exécutées
```

---

## 📊 Performances

### Benchmarks (RTX 4090)

| Opération | Latence Moyenne | Notes |
|-----------|-----------------|-------|
| STT (Whisper) | < 1s | Transcription française |
| LLM Simple | < 3s | Génération 40 tokens/s |
| LLM Complexe | < 5s | Avec recherche contexte |
| TTS (XTTS) | < 0.5s | Voix naturelle |
| Recherche Web | < 3s | 5 sources consultées |
| Commande Système | < 1s | Exécution bash |
| Conversation Complète | < 5s | Bout-en-bout vocal |

### Utilisation des Ressources

| Ressource | Repos | Utilisation Normale | Pic |
|-----------|-------|---------------------|-----|
| VRAM (GPU) | 12 GB | 18 GB | 22 GB |
| RAM | 8 GB | 35 GB | 50 GB |
| CPU | 5% | 30% | 70% |
| GPU | 0% | 70% | 95% |

---

## 🔒 Sécurité

### Principes Fondamentaux

1. **Privacy by Design** : Toutes les données restent locales
2. **Sandbox par Défaut** : Exécution de code isolée dans Docker
3. **Principe du Moindre Privilège** : Permissions granulaires
4. **Auditabilité** : Logs complets de toutes les actions
5. **Chiffrement** : Données sensibles chiffrées (optionnel)

### Niveaux de Permission

| Niveau | Description | Exemples |
|--------|-------------|----------|
| **0** | Lecture seule | Afficher fichiers, informations système |
| **1** | Écriture utilisateur | Créer/modifier fichiers dans ~/home |
| **2** | Système non-privilégié | Commandes bash, gestion processus (défaut) |
| **3** | Installation packages | apt install (avec confirmation) |
| **4** | Administrateur | sudo (confirmation obligatoire) |

### Blacklist de Commandes

Liste des commandes automatiquement bloquées :
- `rm -rf /`
- `dd if=/dev/zero`
- `mkfs.*`
- Fork bombs : `:(){ :|:& };:`
- Et autres patterns dangereux

---

## 🛠️ Développement

### Setup Environnement Local (macOS/Linux)

```bash
# 1. Cloner le repo
git clone https://github.com/jacquesbagui/roxane-os.git
cd roxane-os

# 2. Installer Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 3. Installer les dépendances
poetry install

# 4. Activer l'environnement virtuel
poetry shell

# 5. Configuration
cp .env.example .env
# Éditer .env avec vos paramètres

# 6. Lancer en mode développement
python -m api.server --reload
```

### Tests

```bash
# Tests unitaires
pytest tests/unit/

# Tests d'intégration
pytest tests/integration/

# Tests E2E
pytest tests/e2e/

# Couverture
pytest --cov=core --cov-report=html
```

### Contribuer

Nous accueillons les contributions ! Voici comment participer :

1. **Fork** le repository
2. **Créer** une branche (`git checkout -b feature/AmazingFeature`)
3. **Commiter** vos changements (`git commit -m 'Add AmazingFeature'`)
4. **Pusher** vers la branche (`git push origin feature/AmazingFeature`)
5. **Ouvrir** une Pull Request

Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour plus de détails.

---

## 📚 Documentation

### Guides Complets

- 📖 [Guide Utilisateur](docs/USER_GUIDE.md) - Utilisation quotidienne de Roxane
- 🔧 [Guide Développeur](docs/DEV_GUIDE.md) - Architecture et développement
- 📡 [Référence API](docs/API_REFERENCE.md) - Documentation API REST
- 🏛️ [Architecture](docs/ARCHITECTURE.md) - Design système détaillé
- ❓ [FAQ](docs/FAQ.md) - Questions fréquentes
- 🐛 [Troubleshooting](docs/TROUBLESHOOTING.md) - Résolution de problèmes

### Exemples

Le dossier [examples/](examples/) contient :
- Conversations types
- Commandes système avancées
- Scripts personnalisés
- Intégrations API

---

## 🗺️ Roadmap

### Version 1.1 (Q1 2026)
- [ ] Support multi-utilisateurs
- [ ] Interface web (alternative à PyQt6)
- [ ] Système de plugins
- [ ] LoRA marketplace communautaire
- [ ] Amélioration performances (-30% latence)

### Version 1.5 (Q2 2026)
- [ ] Support GPU AMD (ROCm)
- [ ] Version Raspberry Pi 5 optimisée
- [ ] Mode cloud hybride (optionnel)
- [ ] Application mobile (iOS/Android)
- [ ] Intégrations tierces (Spotify, Home Assistant)

### Version 2.0 (Q3 2026)
- [ ] Multi-modal (vision par ordinateur)
- [ ] Support Windows/macOS natif
- [ ] Agents autonomes (tâches longue durée)
- [ ] Marketplace d'extensions
- [ ] API publique pour développeurs

---

## 🤝 Communauté et Support

### Rejoignez-nous

- 💬 [Discord](https://discord.gg/roxaneos) - Chat communautaire
- 🐦 [Twitter/X](https://twitter.com/roxaneos) - Actualités et annonces
- 📧 [Email](mailto:support@roxaneos.com) - Support technique
- 🎥 [YouTube](https://youtube.com/roxaneos) - Tutoriels vidéo

### Obtenir de l'Aide

**Bug Reports**  
Ouvrez une [issue GitHub](https://github.com/jacquesbagui/roxane-os/issues) avec :
- Description détaillée du problème
- Logs (`/var/log/roxane/roxane.log`)
- Sortie de `/opt/roxane/scripts/check-system.sh`
- Configuration système (OS, RAM, GPU)

**Questions**  
Utilisez [GitHub Discussions](https://github.com/jacquesbagui/roxane-os/discussions) pour :
- Questions d'utilisation
- Propositions de fonctionnalités
- Discussions générales

---

## 📄 Licence

Ce projet est sous licence **Apache 2.0** - voir le fichier [LICENSE](LICENSE) pour plus de détails.

### Licences des Dépendances

Les principaux composants utilisent les licences suivantes :
- LLaMA 3.1 : [Llama Community License](https://ai.meta.com/llama/license/)
- Whisper : MIT License
- Coqui TTS : MPL 2.0 License
- PyQt6 : GPL v3 / Commercial
- FastAPI : MIT License

---

## 🙏 Remerciements

Roxane OS n'existerait pas sans ces projets incroyables :

- [Meta AI](https://ai.meta.com/) - LLaMA models
- [OpenAI](https://openai.com/) - Whisper
- [Coqui](https://coqui.ai/) - XTTS
- [Hugging Face](https://huggingface.co/) - Transformers
- [vLLM](https://github.com/vllm-project/vllm) - Inference engine
- [PostgreSQL](https://www.postgresql.org/) - Database
- [pgvector](https://github.com/pgvector/pgvector) - Vector search
- Et tous les contributeurs open-source

---

## 👥 Équipe

<table>
  <tr>
    <td align="center">
      <img src="https://avatars.githubusercontent.com/u/5459999?s=48&v=4" width="100px;" alt=""/>
      <br /><sub><b>Jacques BAGUI</b></sub>
      <br />Creator & Lead Dev
    </td>
  </tr>
</table>

---

## 📈 Statistiques

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/your-username/roxane-os?style=social)
![GitHub forks](https://img.shields.io/github/forks/your-username/roxane-os?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/your-username/roxane-os?style=social)

![GitHub issues](https://img.shields.io/github/issues/your-username/roxane-os)
![GitHub pull requests](https://img.shields.io/github/issues-pr/your-username/roxane-os)
![GitHub last commit](https://img.shields.io/github/last-commit/your-username/roxane-os)

</div>

---

<div align="center">

**Made with ❤️ by the Roxane OS Community**

[⬆ Retour en haut](#roxane-os)

</div>