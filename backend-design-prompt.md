# Backend Design Master Prompt

You are a **senior backend architect** with deep expertise in designing scalable, secure, and maintainable systems. Your task is to generate a complete backend blueprint for the product idea provided below.

---

## Input

**Product Idea:**  
{{PRODUCT_IDEA}}

---

## Instructions

Based on the product idea above, produce a detailed backend design blueprint. Your output must be structured exactly as described below. Be thorough, justify your choices, and provide concrete recommendations. Use a professional, technical tone.

---

## Output Structure

### 1. Tech Stack

- **Language & Framework** – Specify primary language and web framework (e.g., Node.js + Express, Python + Django, Go + Gin). Give a short rationale.
- **Database** – Choose between SQL (e.g., PostgreSQL) or NoSQL (e.g., MongoDB) and justify. Include any required extensions (e.g., PostGIS, full-text search).
- **Caching** – Recommend caching layer (e.g., Redis, Memcached) and typical use cases.
- **Message Queue / Background Jobs** – If needed, suggest a queue system (e.g., RabbitMQ, Bull, Celery) and why.
- **Other Services** – Any third‑party integrations (e.g., email, SMS, payment, storage) with specific services.

### 2. Database Schema

- Provide **entity‑relationship** descriptions or **table definitions**.
- For each table/collection, list columns/fields with types, constraints, and indexes.
- Show **relationships** (foreign keys, references, embedded documents).
- Mention any **sharding/partitioning** strategy if relevant.

### 3. API Endpoints

- **Architecture style** – RESTful, GraphQL, or gRPC, with a short rationale.
- **Endpoint table** – For each endpoint, specify:
  - HTTP method and path (or GraphQL operation)
  - Request body / parameters (with types)
  - Response structure (success and error)
  - Brief description of business logic
- Group endpoints by domain/resource (e.g., Users, Projects, Tasks).

### 4. Authentication & Authorization

- **Auth mechanism** – e.g., JWT, OAuth2, session‑based. Explain choice.
- **User roles** – Define roles (e.g., Admin, Member, Viewer) and their permissions.
- **Authorization logic** – How permissions are enforced (middleware, decorators, policies).
- **Password hashing** – Algorithm (bcrypt, Argon2) and salt strategy.
- **Session / token storage** – Where tokens are stored (e.g., Redis, client‑side).
- **Additional security** – Rate limiting, CORS, input validation.

### 5. Deployment Notes

- **Environment variables** – List required configuration keys.
- **Containerization** – Dockerfile and orchestration (Kubernetes, Docker Compose) suggestions.
- **CI/CD** – Recommended pipeline (GitHub Actions, GitLab CI) with steps (test, build, deploy).
- **Hosting** – Cloud provider and services (AWS, GCP, Azure, Heroku) with specific offerings (e.g., RDS, EC2, Cloud Run).
- **Monitoring & Logging** – Tools (Prometheus, Grafana, ELK, Sentry) and what to monitor.
- **Scaling** – Horizontal scaling strategies (statelessness, database read replicas, load balancers).
- **Backup & Recovery** – Backup schedule and disaster recovery plan.

---

## Output Format

Produce the final answer as a **single markdown document** with the above five top‑level sections. Use sub‑headings, tables, and bullet points for clarity. Include all relevant details; do not omit any section.

---

## Important Constraints

- Assume a **modern cloud‑native** environment.
- Keep security as a top priority.
- Justify every major decision with a brief “why”.
- If the product idea is ambiguous, make reasonable assumptions and note them.

# Backend Blueprint: Task Management App (Worked Example)

## Product Idea
A multi‑tenant task management application where users can create teams, projects within teams, and tasks. Team members can assign tasks, add comments, and receive real‑time notifications when a task is updated.

---

## 1. Tech Stack

- **Language & Framework** – **Node.js + Express (TypeScript)** for non‑blocking I/O, ideal for real‑time features, and a mature ecosystem.  
- **Database** – **PostgreSQL** for ACID compliance, robust querying, and JSONB support. Use `LISTEN/NOTIFY` for real‑time push notifications.  
- **Caching** – **Redis** for session caching, rate limiting, and as a pub/sub broker for real‑time events.  
- **Message Queue / Background Jobs** – **Bull** (Redis‑based) for scheduled reminders and email notifications.  
- **Other Services** – **SendGrid** (transactional emails), **AWS S3** (file attachments), **Socket.IO** (WebSockets for real‑time updates).

---

## 2. Database Schema

**Database**: PostgreSQL

### Tables

| Table | Columns | Constraints & Indexes |
|-------|---------|------------------------|
| **users** | `id` (UUID, PK), `email` (text, unique), `password_hash` (text), `full_name` (text), `created_at` (timestamp), `updated_at` (timestamp) | Unique email; index on email for login |
| **teams** | `id` (UUID, PK), `name` (text), `slug` (text, unique), `created_by` (UUID → users.id), `created_at`, `updated_at` | Unique slug; index on slug |
| **team_members** | `team_id` (UUID → teams.id), `user_id` (UUID → users.id), `role` (enum: admin, member, viewer), `joined_at` | Composite PK; index on team_id and user_id |
| **projects** | `id` (UUID, PK), `team_id` (UUID → teams.id), `name` (text), `description` (text), `created_by` (UUID → users.id), `created_at`, `updated_at` | Index on team_id |
| **tasks** | `id` (UUID, PK), `project_id` (UUID → projects.id), `title` (text), `description` (text), `status` (enum: backlog, todo, in_progress, review, done), `priority` (integer), `due_date` (timestamp), `assigned_to` (UUID → users.id), `created_by` (UUID → users.id), `created_at`, `updated_at` | Indexes on project_id, assigned_to, status, due_date |
| **comments** | `id` (UUID, PK), `task_id` (UUID → tasks.id), `user_id` (UUID → users.id), `content` (text), `created_at` | Index on task_id |
| **attachments** | `id` (UUID, PK), `task_id` (UUID → tasks.id), `file_url` (text), `uploaded_by` (UUID → users.id), `created_at` | Index on task_id |
| **notifications** | `id` (UUID, PK), `user_id` (UUID → users.id), `type` (text), `data` (JSONB), `read` (boolean), `created_at` | Index on user_id and read |

### Relationships

- A `team` has many `team_members` and many `projects`.  
- A `project` belongs to one `team` and has many `tasks`.  
- A `task` belongs to one `project`, may have an `assigned_to` user, and has many `comments`/`attachments`.  
- `notifications` are scoped per user.

**Additional Indexes**: Add composite indexes for frequent queries, e.g., `(team_id, project_id)` for listing projects within a team.

---

## 3. API Endpoints

- **Architecture**: RESTful API with WebSocket (Socket.IO) for real‑time events.  
- **Authentication**: All endpoints (except register/login) require a valid JWT token in the `Authorization` header.

### REST Endpoints

| Method & Path | Request Body / Params | Response (success) | Description |
|---------------|-----------------------|--------------------|-------------|
| **Auth** ||||
| `POST /api/auth/register` | `{ email, password, fullName }` | `{ user: { id, email, fullName }, token }` | Register new user |
| `POST /api/auth/login` | `{ email, password }` | `{ token, user }` | Login |
| **Teams** ||||
| `POST /api/teams` | `{ name, slug }` | `{ team }` | Create team (creator becomes admin) |
| `GET /api/teams` | Query: `?page=1&limit=20` | `{ teams: [], total }` | List teams user belongs to |
| `GET /api/teams/:teamId` | – | `{ team }` | Get team details |
| `PUT /api/teams/:teamId` | `{ name, slug }` | `{ team }` | Update team (admin only) |
| `DELETE /api/teams/:teamId` | – | `{ message }` | Delete team (admin only) |
| `POST /api/teams/:teamId/members` | `{ userEmail, role }` | `{ member }` | Add member (admin only) |
| `DELETE /api/teams/:teamId/members/:userId` | – | `{ message }` | Remove member (admin only) |
| **Projects** ||||
| `POST /api/teams/:teamId/projects` | `{ name, description }` | `{ project }` | Create project (team member) |
| `GET /api/teams/:teamId/projects` | Query: `?page=1&limit=20` | `{ projects: [], total }` | List projects in team |
| `GET /api/projects/:projectId` | – | `{ project }` | Get project details |
| `PUT /api/projects/:projectId` | `{ name, description }` | `{ project }` | Update project (team member) |
| `DELETE /api/projects/:projectId` | – | `{ message }` | Delete project (admin only) |
| **Tasks** ||||
| `POST /api/projects/:projectId/tasks` | `{ title, description, status, priority, dueDate, assignedTo? }` | `{ task }` | Create task |
| `GET /api/projects/:projectId/tasks` | Query: `?status=…&assignedTo=…&page=1&limit=20` | `{ tasks: [], total }` | List tasks with filters |
| `GET /api/tasks/:taskId` | – | `{ task }` | Get task details |
| `PUT /api/tasks/:taskId` | `{ title, description, status, priority, dueDate, assignedTo }` | `{ task }` | Update task (partial updates allowed) |
| `DELETE /api/tasks/:taskId` | – | `{ message }` | Delete task |
| `POST /api/tasks/:taskId/comments` | `{ content }` | `{ comment }` | Add comment |
| `GET /api/tasks/:taskId/comments` | – | `{ comments: [] }` | List comments |
| `POST /api/tasks/:taskId/attachments` | Multipart/form-data with file | `{ attachment: { fileUrl } }` | Upload attachment |
| **Notifications** ||||
| `GET /api/notifications` | Query: `?read=false&page=1` | `{ notifications: [], total }` | Get user’s notifications |
| `PUT /api/notifications/:id/read` | – | `{ notification }` | Mark as read |
| `PUT /api/notifications/read-all` | – | `{ message }` | Mark all as read |

### WebSocket Events (Socket.IO)

- Client joins rooms: `joinTeam(teamId)`, `joinTask(taskId)`  
- Server emits: `taskUpdated(taskData)`, `commentAdded(commentData)`, `notification(notificationData)`

---

## 4. Authentication & Authorization

- **Auth Mechanism**: **JWT** – stateless access tokens (15 min expiry) + refresh tokens (7 days) stored in HTTP‑only cookies for security.  
- **Password Hashing**: **bcrypt** with salt rounds = 12.  
- **User Roles** (per team):
  - `admin` – full team management, delete projects, manage members.
  - `member` – create/update tasks, add comments.
  - `viewer` – read‑only access.
- **Authorization Logic** – Middleware that:
  1. Validates JWT and extracts user ID.
  2. For team‑scoped routes, ensures user is a member of that team.
  3. For project/task actions, verifies the user belongs to the project’s team.
  4. For destructive writes, checks role permission (admin required).
- **Rate Limiting**: `express‑rate‑limit` with Redis store – 100 req/min per user (general), 5 req/min for auth endpoints.
- **CORS**: Restrict to allowed frontend domains.
- **Input Validation**: Use **Joi** or **class‑validator** to sanitize and validate all payloads.

---

## 5. Deployment Notes

### Environment Variables


### Containerization
- Multi‑stage **Dockerfile** with Node.js Alpine image.
- `docker‑compose.yml` for local development (app, postgres, redis, pgadmin).

### CI/CD
- **GitHub Actions** workflow on push to `main`:
  - Run tests → Build Docker image → Push to **AWS ECR** → Deploy to **AWS ECS (Fargate)** with rolling updates.

### Hosting (AWS)
- **ECS Fargate** – serverless container orchestration.
- **RDS for PostgreSQL** – Multi‑AZ for high availability.
- **ElastiCache for Redis** – caching and pub/sub.
- **S3** – file storage.
- **CloudFront + S3** – static asset delivery.
- **Application Load Balancer (ALB)** – traffic distribution.

### Monitoring & Logging
- **Prometheus + Grafana** – metrics (latency, error rates, DB pool).
- **AWS CloudWatch** – logs and alarms.
- **Sentry** – error tracking.

### Scaling
- Stateless app servers → Horizontal scaling via ECS auto‑scaling (CPU/memory).
- Database read replicas for read‑heavy workloads.
- Redis clustering if pub/sub load increases.

### Backup & Recovery
- RDS automated daily snapshots with 7‑day retention.
- S3 versioning enabled for file backups.
- Cross‑region replica for RDS and S3 as disaster recovery.

---

*This blueprint can be adapted to other product ideas by substituting the domain entities and adjusting integrations.*
