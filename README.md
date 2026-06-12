# Exam Observabilite

Plateforme d'observabilite complete pour une application de restaurant en microservices Python. Le projet livre une pile prete a l'emploi pour les metriques, les logs et les traces, ainsi qu'une documentation de cadrage SLI/SLO/SLA et un scenario de gestion d'incident.

## Demarrage rapide

```bash
docker compose up -d --build
```

Interfaces principales :

- Grafana : http://localhost:3000 (`admin` / `admin`)
- Prometheus : http://localhost:9090
- Jaeger : http://localhost:16686
- RabbitMQ : http://localhost:15672

## Contenu livre

- Dashboards Grafana provisionnes automatiquement :
  - `Restaurant Metrics Overview`
  - `Restaurant Logs Overview`
  - `Restaurant Traces Overview`
- Centralisation des logs applicatifs via Fluent Bit vers Loki
- Tracing distribue OpenTelemetry vers Jaeger
- Metriques Prometheus applicatives et d'infrastructure
- Rapport projet : [docs/RAPPORT_PROJET.md](/root/Exam-observabilite/docs/RAPPORT_PROJET.md)
- Schema d'architecture : [docs/architecture.mmd](/root/Exam-observabilite/docs/architecture.mmd)
  - Rendu SVG : [docs/architecture.svg](/root/Exam-observabilite/docs/architecture.svg)

## Structure observabilite

- `observability/prometheus/` : scraping Prometheus
- `observability/fluent-bit/` : collecte et enrichissement des logs
- `observability/loki/` : stockage et indexation des logs
- `observability/grafana/` : datasources et dashboards provisionnes

## Rejouer l'incident de paiement

Par defaut, l'environnement est sain. Pour reproduire la panne documentee dans le rapport, activez le chaos du service paiement :

```bash
docker compose down
PAYMENT_CHAOS_ENABLED=true docker compose up -d --build
```

Le symptome attendu est une hausse des erreurs `503` et de la latence sur le service `payment`.
