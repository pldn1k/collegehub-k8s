# CollegeHub - Микросервисное приложение для колледжа

## Описание
Учебный портал для студентов и преподавателей. Реализована аутентификация, оценки, расписание, мониторинг.

## Архитектура
- **Frontend** — Nginx + HTML/JS
- **API Gateway** — Flask, единая точка входа
- **Auth Service** — JWT, Redis, PostgreSQL
- **PostgreSQL** — хранение данных
- **Redis** — сессии
- **Prometheus + Grafana** — мониторинг

## Запуск (локально, Kind)
```bash
kind create cluster
kind load docker-image auth-service:latest
kind load docker-image api-gateway:latest
kind load docker-image frontend:latest

kubectl apply -f manifests/
# collegehub-k8s
