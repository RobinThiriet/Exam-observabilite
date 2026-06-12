# Rapport de projet - Mise en place d'un systeme d'observabilite

## 1. Resume executif

L'architecture du restaurant a ete instrumentee avec une pile unifiee `Prometheus + Grafana + Fluent Bit + Elasticsearch + Kibana + Jaeger + OpenTelemetry + cAdvisor`. L'objectif etait de couvrir les trois piliers de l'observabilite demandee par la consigne : metriques, logs et traces.

Le resultat permet :

- de mesurer la sante de l'application et des conteneurs ;
- de centraliser les logs applicatifs et de les rechercher par `reservation_id` ;
- de suivre un parcours distribue complet depuis la reservation jusqu'au paiement ;
- d'identifier rapidement une panne grace a la correlation logs, traces et metriques.

## 2. Choix technologiques

### 2.1 Metriques

- `Prometheus` collecte les endpoints `/metrics` des APIs Flask et les endpoints Prometheus exposes par `customer` et `kitchen`.
- `cAdvisor` collecte les metriques conteneurs pour l'ensemble des services deployes.
- `Grafana` visualise les indicateurs metier et d'infrastructure dans le dashboard `Restaurant Metrics Overview`.

### 2.2 Logs

- Les services Python ecrivent dans un volume partage `/var/log/restaurant`.
- `Fluent Bit` collecte ces fichiers, parse le niveau de log, le `trace_id`, le `span_id` et le `reservation_id`.
- `Elasticsearch` stocke les logs centralises.
- `Kibana` fournit le dashboard logs et une recherche plein texte exploitable.

### 2.3 Traces

- Le code fourni etait deja partiellement instrumente avec `OpenTelemetry`.
- Les spans HTTP, RabbitMQ, Redis et PostgreSQL sont exportes en OTLP vers `Jaeger`.
- `Grafana` est provisionne avec une datasource Jaeger et un dashboard `Restaurant Traces Overview`.
- `Jaeger` reste l'outil principal de drill-down des traces distribuees.

## 3. Instructions de lancement

### 3.1 Pre-requis

- Docker
- Docker Compose
- 4 Go de RAM recommandes

### 3.2 Demarrage

```bash
docker compose up -d --build
```

### 3.3 Endpoints utiles

- Grafana : http://localhost:3000
- Prometheus : http://localhost:9090
- Jaeger : http://localhost:16686
- RabbitMQ Management : http://localhost:15672
- Waiter API : http://localhost:5001
- Payment API : http://localhost:5003
- Reservation API : http://localhost:5004

## 4. SLI, SLO et SLA

### 4.1 SLI retenus

| Domaine | SLI | Definition | Source |
| --- | --- | --- | --- |
| Disponibilite | Taux de succes des paiements | `payments_success / payments_total` | Prometheus |
| Performance | Latence P95 paiement | `histogram_quantile` sur `restaurant_payment_processing_seconds` | Prometheus |
| Debit | Debit de reservations | `rate(restaurant_reservations_created_total)` | Prometheus |
| Continuite de service | Nombre de reservations actives | `restaurant_active_reservations` | Prometheus |
| Fiabilite des dependances | Taux d'erreurs de dependances | `restaurant_dependency_failures_total` | Prometheus |
| Investigabilite | Recherche de logs par reservation | presence du champ `reservation_id` | Kibana |
| Tracabilite | Reconstitution d'un parcours distribue | trace complete HTTP + RabbitMQ + Redis + PostgreSQL | Jaeger |

### 4.2 SLO proposes

| SLI | SLO |
| --- | --- |
| Taux de succes des paiements | >= 99 % sur 30 jours |
| Latence P95 paiement | < 1,5 s sur 95 % des requetes |
| Disponibilite des APIs `reservation`, `waiter`, `payment` | >= 99,5 % sur 30 jours |
| Taux d'erreurs de dependances critiques | < 1 % sur 1 heure glissante |
| Logs correlables par `reservation_id` | 100 % des transactions metier doivent etre recherchables |
| Traces distribuées des flux critiques | >= 95 % des parcours doivent produire une trace exploitable |

### 4.3 SLA propose

Le service garanti au client :

- une disponibilite mensuelle de 99,5 % des parcours de commande ;
- un taux de succes des paiements de 99 % ;
- un temps de traitement de paiement inferieur a 1,5 s au P95.

En cas de non-respect du SLA sur un mois civil :

- credit de service de 10 % si un seul engagement est manque ;
- credit de service de 20 % si deux engagements ou plus sont manques ;
- ouverture obligatoire d'un rapport d'incident et plan d'actions correctives.

## 5. Dashboards livres

### 5.1 Dashboard metriques

`Restaurant SLI SLO SLA Overview` couvre :

- debit de reservations ;
- taux d'erreur paiement ;
- latence P95 paiement ;
- reservations actives ;
- transitions de statuts ;
- erreurs de dependances ;
- CPU et memoire des conteneurs.

### 5.2 Dashboard logs

`Restaurant Logs Dashboard` dans Kibana couvre :

- recherche plein texte ;
- filtrage par service ;
- correlation via `trace_id` et `reservation_id`.

### 5.3 Dashboard traces

`Restaurant Traces & Root Cause` permet :

- de coller un `trace_id` issu des logs ;
- de visualiser la trace dans Grafana ;
- de poursuivre l'analyse detaillee dans Jaeger.

## 6. Gestion d'incident

### 6.1 Incident choisi

Une panne volontaire de type `Payment Gateway Timeout` etait presente dans le service `payment`. Elle introduisait aleatoirement :

- une latence de 2,5 s ;
- des reponses HTTP `503`.

### 6.2 Consequence observable

Les symptomes attendus sont :

- augmentation du `Payment Error Rate` ;
- degradation du `Payment Latency P95` ;
- apparition de logs `CRITICAL: Payment Gateway Timeout` ;
- traces de paiement plus longues ou terminees en echec.

### 6.3 Source de la panne

La source etait un bloc de chaos engineering active en dur dans `payment/payment.py`. Il simulait un timeout reseau vers une banque externe, sans mecanisme de bascule ni activation conditionnelle.

### 6.4 Resolution apportee

La correction livree consiste a :

- desactiver la panne par defaut ;
- conserver un mode de reproduction via la variable `PAYMENT_CHAOS_ENABLED=true` ;
- exposer des metriques dediees pour mesurer les echecs et la latence ;
- permettre une validation normale du parcours applicatif en environnement standard.

### 6.5 Communication de crise

Destinataires :

- equipe exploitation ;
- responsable technique ;
- parties prenantes metier impactees.

Message propose :

> Incident en cours sur la chaine de paiement du restaurant. Nous observons une hausse des erreurs `503` et une augmentation de la latence sur le service `payment`. Les reservations et commandes continuent d'etre traitees, mais une partie des paiements echoue temporairement. L'analyse pointe un timeout sur la dependance bancaire simulee. Une mesure corrective est en cours de deploiement, avec retour a la normale estime apres redemarrage du service paiement.

Pourquoi communiquer :

- partager l'impact client visible ;
- aligner les equipes sur la cause probable ;
- donner un ETA et limiter l'incertitude.

## 7. Architecture logicielle

Le schema source est disponible dans [docs/architecture.mmd](/root/Exam-observabilite/docs/architecture.mmd) et en rendu dans [docs/architecture.svg](/root/Exam-observabilite/docs/architecture.svg).

Vue d'ensemble :

- `customer` genere la charge et declenche le parcours client ;
- `reservation` enregistre la reservation dans Redis puis publie sur RabbitMQ ;
- `waiter` orchestre menu, commande et notifications ;
- `kitchen` consomme les commandes puis notifie leur preparation ;
- `payment` persiste la transaction dans PostgreSQL et clot la reservation ;
- la couche observabilite collecte metriques, logs et traces sur l'ensemble des composants.

## 8. Limites et pistes d'amelioration

- Ajouter des screenshots reelles des dashboards apres execution de la charge.
- Ajouter des alertes Grafana ou Alertmanager sur les SLO critiques.
- Exposer aussi des exporters dedies pour PostgreSQL, Redis et RabbitMQ si une granularite d'infrastructure plus fine est necessaire.
