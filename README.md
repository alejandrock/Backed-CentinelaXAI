# CentinelaX AI — Backend

## Plataforma Inteligente de Ciberseguridad Multidominio

**CentinelaX AI Backend** es el núcleo de servicios API de la plataforma CentinelaX AI, una solución inteligente de ciberseguridad orientada a detectar, analizar, correlacionar y explicar amenazas provenientes de múltiples dominios: URLs sospechosas, phishing, logs Linux, blockchain/Web3 y fuentes externas de Threat Intelligence.

El backend está construido con **FastAPI**, integrando autenticación segura, control de acceso basado en roles, validación estricta de datos, persistencia en PostgreSQL y módulos de inteligencia artificial para análisis de amenazas.

---

## Objetivo del Backend

El objetivo principal del backend es proporcionar una capa segura, escalable y modular para:

- Gestionar autenticación y autorización de usuarios.
- Exponer endpoints REST para análisis de amenazas.
- Procesar URLs sospechosas y detectar phishing.
- Integrar modelos de IA/ML para clasificación y scoring.
- Persistir eventos, incidentes, resultados y auditoría.
- Servir como capa de orquestación entre frontend, modelos IA, base de datos y futuras integraciones.
- Preparar la plataforma para correlación multidominio y explicación mediante LLM.

---

## Arquitectura General

El backend forma parte de una arquitectura por capas:

```text
Frontend React
     |
     v
FastAPI Backend
     |
     +-- Auth / JWT / RBAC
     +-- URL Analysis Service
     +-- Phishing Detection Service
     +-- Incident Management
     +-- Correlation Engine
     +-- Threat Intelligence Integration
     |
     v
PostgreSQL
     |
     +-- Users
     +-- Roles
     +-- Incidents
     +-- Events
     +-- Audit Logs