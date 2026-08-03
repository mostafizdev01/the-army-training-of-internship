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

Worked Example: Task Management App with Teams, Projects, and Real‑time Updates
Product Idea:
A multi‑tenant task management application where users can create teams, projects within teams, and tasks. Team members can assign tasks, add comments, and receive real‑time notifications when a task is updated.

1. Tech Stack
Language & Framework – Node.js + Express (TypeScript) for its non‑blocking I/O, great for real‑time features, and large ecosystem.

Database – PostgreSQL for ACID compliance, rich querying, and support for JSONB (to store flexible metadata). Use PostgreSQL’s LISTEN/NOTIFY for real‑time push.

Caching – Redis for session caching, rate limiting, and as a pub/sub broker for real‑time events.

Message Queue / Background Jobs – Bull (Redis‑based) for scheduled reminders and email notifications.

Other Services – SendGrid for transactional emails, AWS S3 for file attachments, Socket.IO (WebSockets) for real‑time updates.

2. Database Schema
Entities (PostgreSQL tables):

Table	Columns	Constraints & Indexes
users	id (UUID, PK), email (text, unique), password_hash (text), full_name (text), created_at (timestamp), updated_at (timestamp)	Unique on email; index on email for login
teams	id (UUID, PK), name (text), slug (text, unique), created_by (UUID → users.id), created_at, updated_at	Unique slug; index on slug
team_members	team_id (UUID → teams.id), user_id (UUID → users.id), role (enum: admin, member, viewer), joined_at	Composite PK; index on team_id and user_id
projects	id (UUID, PK), team_id (UUID → teams.id), name (text), description (text), created_by (UUID → users.id), created_at, updated_at	Index on team_id
tasks	id (UUID, PK), project_id (UUID → projects.id), title (text), description (text), status (enum: backlog, todo, in_progress, review, done), priority (integer), due_date (timestamp), assigned_to (UUID → users.id), created_by (UUID → users.id), created_at, updated_at	Index on project_id, assigned_to, status, due_date
comments	id (UUID, PK), task_id (UUID → tasks.id), user_id (UUID → users.id), content (text), created_at	Index on task_id
attachments	id (UUID, PK), task_id (UUID → tasks.id), file_url (text), uploaded_by (UUID → users.id), created_at	Index on task_id
notifications	id (UUID, PK), user_id (UUID → users.id), type (text), data (JSONB), read (boolean), created_at	Index on user_id and read
Relationships:

A team has many team_members and many projects.

A project belongs to one team and has many tasks.

A task belongs to one project, has optional assigned_to user, and has many comments and attachments.

Notifications are per user.

Indexes: Add composite indexes for frequent queries (e.g., (team_id, project_id) for listing projects in a team).

3. API Endpoints
Architecture: RESTful with WebSocket (Socket.IO) for real‑time events.

Authentication: All endpoints require a valid JWT token in the Authorization header (except login/signup).

Method & Path	Request Body / Params	Response (success)	Description
Auth			
POST /api/auth/register	{ email, password, fullName }	{ user: { id, email, fullName }, token }	Register new user
POST /api/auth/login	{ email, password }	{ token, user }	Login
Teams			
POST /api/teams	{ name, slug }	{ team }	Create team (creator becomes admin)
GET /api/teams	(query: ?page=1&limit=20)	{ teams: [], total }	List teams the user belongs to
GET /api/teams/:teamId	–	{ team }	Get team details
PUT /api/teams/:teamId	{ name, slug }	{ team }	Update team (admin only)
DELETE /api/teams/:teamId	–	{ message }	Delete team (admin only)
POST /api/teams/:teamId/members	{ userEmail, role }	{ member }	Add member to team (admin only)
DELETE /api/teams/:teamId/members/:userId	–	{ message }	Remove member
Projects			
POST /api/teams/:teamId/projects	{ name, description }	{ project }	Create project (team member)
GET /api/teams/:teamId/projects	(query: ?page=1&limit=20)	{ projects: [], total }	List projects in team
GET /api/projects/:projectId	–	{ project }	Get project details
PUT /api/projects/:projectId	{ name, description }	{ project }	Update project (team member)
DELETE /api/projects/:projectId	–	{ message }	Delete project (admin only)
Tasks			
POST /api/projects/:projectId/tasks	{ title, description, status, priority, dueDate, assignedTo? }	{ task }	Create task
GET /api/projects/:projectId/tasks	query: ?status=…&assignedTo=…&page=1&limit=20	{ tasks: [], total }	List tasks with filters
GET /api/tasks/:taskId	–	{ task }	Get task details
PUT /api/tasks/:taskId	{ title, description, status, priority, dueDate, assignedTo }	{ task }	Update task (partial updates allowed)
DELETE /api/tasks/:taskId	–	{ message }	Delete task
POST /api/tasks/:taskId/comments	{ content }	{ comment }	Add comment
GET /api/tasks/:taskId/comments	–	{ comments: [] }	List comments
POST /api/tasks/:taskId/attachments	multipart/form-data with file	{ attachment: { fileUrl } }	Upload attachment
Notifications			
GET /api/notifications	query: ?read=false&page=1	{ notifications: [], total }	Get user’s notifications
PUT /api/notifications/:id/read	–	{ notification }	Mark as read
PUT /api/notifications/read-all	–	{ message }	Mark all as read
WebSocket Events (Socket.IO):

Client joins a room: joinTeam(teamId), joinTask(taskId).

Server emits: taskUpdated(taskData), commentAdded(commentData), notification(notificationData).

4. Authentication & Authorization
Auth mechanism: JWT (stateless) with short‑lived access tokens (15 min) and refresh tokens (7 days) stored in HTTP‑only cookies for enhanced security.

Password hashing: bcrypt with salt rounds = 12.

User roles (per team):

admin – full team management, delete projects, manage members.

member – can create/update tasks, add comments.

viewer – read‑only access.

Authorization logic: A middleware checks:

Valid JWT and extracts user ID.
For team‑scoped routes (e.g., /teams/:teamId/...), ensure the user is a member of that team.
For project/task actions, verify the user belongs to the project’s team.
For write/modify operations, check the role against required permission (admin for destructive actions).
Rate limiting: Implement express‑rate‑limit with Redis store – 100 requests per minute per user for most endpoints; stricter for authentication (5 per minute).

CORS: Restrict to allowed frontend domains.

Input validation: Use Joi or class‑validator to sanitize and validate all inputs.

5. Deployment Notes
Environment Variables:

DATABASE_URL (PostgreSQL connection string)

REDIS_URL

JWT_SECRET, REFRESH_TOKEN_SECRET

SENDGRID_API_KEY

AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET

CLIENT_URL (for CORS)

PORT

Containerization:

Multi‑stage Dockerfile with Node.js alpine.

Use docker‑compose.yml for local development (app, postgres, redis, pgadmin).

CI/CD:

GitHub Actions workflow: on push to main, run tests, build Docker image, push to AWS ECR, and deploy to AWS ECS (Fargate) with rolling updates.

Hosting:

AWS:

ECS Fargate for container orchestration (serverless).

RDS for PostgreSQL with Multi‑AZ for high availability.

ElastiCache for Redis for caching and pub/sub.

S3 for file storage.

CloudFront + S3 for serving static assets.

Application Load Balancer (ALB) for distributing traffic.

Monitoring & Logging:

Prometheus + Grafana for metrics (request latency, error rates, DB connection pool).

AWS CloudWatch for logs and alarms.

Sentry for error tracking.

Scaling:

Stateless app servers ⇒ horizontal scaling via ECS service auto‑scaling based on CPU/memory.

Database read replicas for read‑heavy workloads.

Redis clustering if pub/sub load grows.

Backup & Recovery:

RDS automated daily snapshots with 7‑day retention.

S3 versioning enabled for file backups.

Disaster recovery: cross‑region replica of RDS and S3.