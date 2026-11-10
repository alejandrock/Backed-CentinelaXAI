# CentinelaXAI Flask Identity & Access Backend

Backend Flask diseñado a partir del frontend React/Vite de CentinelaXAI. El frontend adjunto contiene vistas estáticas de **Login**, **Usuarios y roles** y **Perfil**; este proyecto convierte esas vistas en funciones reales de autenticación, RBAC, auditoría y persistencia.

## Alcance implementado

- Login con contraseña Argon2id.
- Access + refresh JWT en cookies HttpOnly.
- Protección CSRF para operaciones autenticadas.
- Bloqueo temporal después de intentos de login fallidos.
- Logout y revocación de tokens.
- Usuarios activos/inactivos.
- Roles y permisos RBAC.
- Roles base: `admin`, `soc_analyst`, `linux_admin`, `security_auditor`, `viewer`.
- Auditoría persistente de accesos y cambios de seguridad.
- Logs estructurados a stdout para Docker.
- PostgreSQL en producción; SQLite soportado para tests.
- Health checks `/api/v1/health/live` y `/api/v1/health/ready`.
- API protegida con formato de error estándar.
- Dockerfile no-root (UID 10001).

## Arquitectura recomendada

```text
Browser
   |
   v
Nginx host :80/:443
   |------------------------------|
   v                              v
/ -> 127.0.0.1:8080          /api/ -> 127.0.0.1:8000
frontend Docker                    Flask backend Docker
                                       |
                                       v
                                 PostgreSQL Docker
                                       |
                                       v
                            /srv/centinelax/postgres
```

Código fuente recomendado:

```text
/home/kir4/projects/centinelaxai-workspace/
├── frontend/
├── backend/      <- este proyecto
└── infra/
    └── compose/
```

## Endpoints principales

| Método | Endpoint | Permiso / uso |
|---|---|---|
| POST | `/api/v1/auth/login` | Público |
| POST | `/api/v1/auth/refresh` | Refresh cookie |
| POST | `/api/v1/auth/logout` | Usuario autenticado |
| GET | `/api/v1/auth/me` | Usuario autenticado |
| POST | `/api/v1/auth/change-password` | Fresh token |
| GET | `/api/v1/users` | `users.read` |
| POST | `/api/v1/users` | `users.create` |
| PATCH | `/api/v1/users/<id>` | `users.update` |
| PUT | `/api/v1/users/<id>/roles` | `users.assign_roles` |
| GET | `/api/v1/roles` | `rbac.read` |
| POST | `/api/v1/roles` | `rbac.manage` |
| PUT | `/api/v1/roles/<id>/permissions` | `rbac.manage` |
| GET | `/api/v1/permissions` | `rbac.read` |
| GET | `/api/v1/audit-logs` | `audit.read` |
| GET | `/api/v1/health/live` | Público |
| GET | `/api/v1/health/ready` | Público |

## Instalación local

Python recomendado: **3.13**, alineado con CentinelaXAI.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Cambia `SECRET_KEY`, `JWT_SECRET_KEY`, contraseñas y `DATABASE_URL` antes de desplegar.

### Crear esquema y RBAC inicial

Para laboratorio/desarrollo inicial:

```bash
export FLASK_APP=wsgi:app
flask bootstrap
```

`bootstrap` crea tablas y roles base. Para un repositorio productivo de larga vida, el siguiente paso es generar y versionar migraciones Flask-Migrate (`flask db init`, `flask db migrate`, `flask db upgrade`) en lugar de depender permanentemente de `db.create_all()`.

## Docker / servidor

Copia el proyecto como:

```text
/home/kir4/projects/centinelaxai-workspace/backend
```

Crea `.env` a partir de `.env.example`. Usa secretos fuertes y no los subas a Git.

El archivo `deploy/docker-compose.backend.yml` es un ejemplo para integrarlo en tu `infra/compose/docker-compose.prod.yml`. El backend se publica solo en:

```text
127.0.0.1:8000
```

PostgreSQL no publica puerto al LAN.

Después de arrancar los contenedores:

```bash
docker compose exec backend flask bootstrap
curl http://127.0.0.1:8000/api/v1/health/live
curl http://127.0.0.1:8000/api/v1/health/ready
```

## Integración con el frontend actual

El frontend analizado tiene Login, Usuarios y Perfil todavía hard-codeados en `src/App.jsx`. El archivo `frontend-api.js` incluido aquí puede copiarse a:

```text
frontend/src/api.js
```

El navegador debe usar `credentials: 'include'` porque los JWT viven en cookies HttpOnly.

Ejemplo de login:

```js
import { api } from './api';

const result = await api.login(email, password);
console.log(result.data.user);
```

Consulta del usuario autenticado:

```js
const result = await api.me();
const user = result.data;
```

La visibilidad de menús puede usar `user.permissions`, pero **la seguridad real siempre la aplica Flask**. Ocultar un botón en React no reemplaza RBAC del backend.

### CSRF

En operaciones `POST`, `PUT`, `PATCH` y `DELETE`, `frontend-api.js` envía automáticamente `X-CSRF-TOKEN` desde la cookie `cx_csrf_access`.

Para el endpoint `/auth/refresh`, si lo automatizas en frontend, usa el token de la cookie `cx_csrf_refresh`.

## Nginx

`deploy/nginx-centinelax.conf` muestra la configuración recomendada para el Nginx del host:

- `/` -> frontend Docker `127.0.0.1:8080`
- `/api/` -> backend Flask `127.0.0.1:8000`
- rate limit adicional para `/api/v1/auth/login`

Con esta estrategia frontend y backend comparten origen (`http(s)://centinelax...`) y se evita CORS en producción.

## Seguridad aplicada

1. Argon2id para passwords; nunca texto plano.
2. JWT HttpOnly cookies; no almacenar access token en localStorage.
3. CSRF double-submit de Flask-JWT-Extended.
4. Lockout básico de cuenta por intentos fallidos.
5. Roles/permisos verificados en servidor en cada request.
6. Audit log separado de logs operativos.
7. Contenedor backend no-root.
8. PostgreSQL sin puerto público.
9. Nginx como único punto de entrada.
10. Secrets mediante `.env` protegido o, en una fase posterior, Vault/secrets manager.

## Pruebas

```bash
pytest
ruff check .
```

Los tests incluidos validan login, rechazo de credenciales, RBAC y generación de auditoría.

## Importante antes de producción

- Habilitar HTTPS y `JWT_COOKIE_SECURE=true`.
- Sustituir `bootstrap/db.create_all()` por migraciones versionadas.
- Rotar y proteger `JWT_SECRET_KEY`/`SECRET_KEY`.
- Integrar Vault o un secrets manager.
- Añadir MFA para administradores.
- Añadir recuperación de contraseña con tokens de un solo uso.
- Integrar alertas sobre lockouts, cambios de roles y eventos administrativos.
- Exportar logs/audit a la capa de observabilidad/SIEM de CentinelaXAI.
