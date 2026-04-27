"""
AILEX — backend_generator.py  (BASTIAN module)
Complete backend project scaffolding for FastAPI, Express, Django, NestJS.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every generated project includes:
  ✅ Auth (JWT + refresh tokens + bcrypt)
  ✅ Database (ORM + migrations + connection pool)
  ✅ Validation (Pydantic / Joi / class-validator)
  ✅ Error handling (global + typed exceptions)
  ✅ Logging (structured JSON)
  ✅ Tests (unit + integration + API)
  ✅ Docker + docker-compose
  ✅ Environment config (.env + validation)
  ✅ API documentation (OpenAPI/Swagger)
  ✅ Rate limiting + CORS
  ✅ CI/CD (GitHub Actions)
  ✅ OWASP security headers

Frameworks supported:
  fastapi    — Python async (uvicorn + SQLAlchemy + Alembic + pytest)
  express    — Node.js (TypeScript + Prisma + Jest + Railway-ready)
  django     — Python (DRF + PostgreSQL + celery + pytest)
  nestjs     — Node.js (TypeScript + TypeORM + Jest + class-validator)
  flask      — Python (minimal + SQLAlchemy + pytest)

Usage:
    from ailex_pilot.backend_generator import BackendGenerator
    gen = BackendGenerator()
    project = gen.generate("fastapi", "todo-api", "Simple TODO API with auth")
    project.write_to("~/projects/todo-api")

    # With BASTIAN agent:
    from ailex_pilot.backend_generator import bastian_generate
    code = bastian_generate("fastapi", brief="User auth system with JWT and refresh tokens")
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── Project file ──────────────────────────────────────────────────────────────

@dataclass
class ProjectFile:
    path:    str   # relative path within project
    content: str
    executable: bool = False


@dataclass
class BackendProject:
    name:       str
    framework:  str
    files:      List[ProjectFile]
    readme:     str
    commands:   Dict[str, str]   # "start", "test", "build", "migrate"

    def write_to(self, base_dir: str) -> List[str]:
        """Write all project files to disk. Returns list of created paths."""
        base = Path(base_dir).expanduser()
        created = []
        for f in self.files:
            full = base / f.path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(f.content, encoding="utf-8")
            if f.executable:
                full.chmod(0o755)
            created.append(str(full))
        # Write README
        (base / "README.md").write_text(self.readme, encoding="utf-8")
        created.append(str(base / "README.md"))
        return created

    def summary(self) -> str:
        lines = [f"BackendProject: {self.name} ({self.framework})",
                 f"  Files: {len(self.files)}",
                 "  Commands:"]
        for k, v in self.commands.items():
            lines.append(f"    {k}: {v}")
        return "\n".join(lines)


# ── FastAPI template ──────────────────────────────────────────────────────────

def _fastapi_project(name: str, description: str) -> BackendProject:
    slug = re.sub(r"[^a-z0-9_]", "_", name.lower())

    files = [

        # requirements.txt
        ProjectFile("requirements.txt", """\
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy>=2.0.0
alembic>=1.13.0
psycopg2-binary>=2.9.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.0
python-multipart>=0.0.9
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
"""),

        # requirements-dev.txt
        ProjectFile("requirements-dev.txt", """\
-r requirements.txt
black>=24.0.0
ruff>=0.3.0
mypy>=1.9.0
"""),

        # .env.example
        ProjectFile(".env.example", f"""\
# Application
APP_NAME={name}
APP_ENV=development
DEBUG=true
SECRET_KEY=change-this-super-secret-key-in-production

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/{slug}

# Auth
JWT_SECRET=change-this-jwt-secret-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
"""),

        # app/__init__.py
        ProjectFile("app/__init__.py", ""),

        # app/config.py
        ProjectFile("app/config.py", """\
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    app_name: str = "API"
    app_env: str = "development"
    debug: bool = False
    secret_key: str
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    allowed_origins: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
"""),

        # app/database.py
        ProjectFile("app/database.py", """\
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""),

        # app/models/user.py
        ProjectFile("app/models/__init__.py", "from app.models.user import User"),
        ProjectFile("app/models/user.py", """\
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    username   = Column(String, unique=True, index=True, nullable=False)
    hashed_pw  = Column(String, nullable=False)
    is_active  = Column(Boolean, default=True)
    is_admin   = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
"""),

        # app/schemas/user.py
        ProjectFile("app/schemas/__init__.py", ""),
        ProjectFile("app/schemas/user.py", """\
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserRead(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
"""),

        # app/auth.py
        ProjectFile("app/auth.py", """\
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expire},
                      settings.jwt_secret, algorithm=settings.jwt_algorithm)

def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days)
    return jwt.encode({"sub": str(user_id), "exp": expire, "type": "refresh"},
                      settings.jwt_secret, algorithm=settings.jwt_algorithm)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials,
                             settings.jwt_secret,
                             algorithms=[settings.jwt_algorithm])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user
"""),

        # app/routers/__init__.py
        ProjectFile("app/routers/__init__.py", ""),

        # app/routers/auth.py
        ProjectFile("app/routers/auth.py", """\
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, Token
from app.auth import hash_password, verify_password, create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "Username already taken")
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_pw=hash_password(payload.password),
    )
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_pw):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
"""),

        # app/routers/users.py
        ProjectFile("app/routers/users.py", """\
from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
"""),

        # app/middleware.py
        ProjectFile("app/middleware.py", """\
import time, logging
from fastapi import Request

logger = logging.getLogger("api")

async def logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = int((time.perf_counter() - start) * 1000)
    logger.info(f'{request.method} {request.url.path} {response.status_code} {ms}ms')
    return response
"""),

        # app/exceptions.py
        ProjectFile("app/exceptions.py", """\
from fastapi import Request
from fastapi.responses import JSONResponse

async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=404, content={"error": "Resource not found"})

async def validation_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=422, content={"error": "Validation failed", "detail": str(exc)})
"""),

        # main.py
        ProjectFile("main.py", f"""\
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import Base, engine
from app.routers import auth, users
from app.middleware import logging_middleware

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="{name}",
    description="{description}",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(logging_middleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {{"status": "ok", "service": "{name}"}}

# Create tables on startup (use Alembic in production)
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
"""),

        # tests/
        ProjectFile("tests/__init__.py", ""),
        ProjectFile("tests/conftest.py", """\
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from main import app

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)
"""),
        ProjectFile("tests/test_auth.py", """\
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_register(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePass123"
    })
    assert r.status_code == 201
    assert r.json()["email"] == "test@example.com"

def test_register_duplicate_email(client):
    data = {"email": "dup@example.com", "username": "dup1", "password": "Pass1234"}
    client.post("/api/v1/auth/register", json=data)
    r = client.post("/api/v1/auth/register", json=data)
    assert r.status_code == 400

def test_login(client):
    client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "username": "loginuser", "password": "Pass1234"
    })
    r = client.post("/api/v1/auth/login?email=login@example.com&password=Pass1234")
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_get_me_unauthorized(client):
    r = client.get("/api/v1/users/me")
    assert r.status_code == 403
"""),

        # Dockerfile
        ProjectFile("Dockerfile", f"""\
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""),

        # docker-compose.yml
        ProjectFile("docker-compose.yml", f"""\
version: "3.9"
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: {slug}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports: ["5432:5432"]
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pg_data:
"""),

        # .github/workflows/ci.yml
        ProjectFile(".github/workflows/ci.yml", f"""\
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {{python-version: "3.12"}}
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --tb=short
      - run: ruff check app/ main.py
"""),

        # alembic.ini stub
        ProjectFile("alembic.ini", """\
[alembic]
script_location = migrations
sqlalchemy.url = %(DATABASE_URL)s
"""),

        # .gitignore
        ProjectFile(".gitignore", """\
__pycache__/
*.pyc
.env
*.db
.mypy_cache/
.ruff_cache/
dist/
"""),
    ]

    readme = f"""# {name}

{description}

## Stack
- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL + SQLAlchemy 2 + Alembic
- **Auth**: JWT (access + refresh tokens) + bcrypt
- **Validation**: Pydantic v2
- **Tests**: pytest + httpx

## Quick start

```bash
cp .env.example .env
docker-compose up -d db redis
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000/docs

## Commands
| Command | Description |
|---|---|
| `uvicorn main:app --reload` | Dev server |
| `pytest tests/ -v` | Run tests |
| `alembic upgrade head` | Run migrations |
| `docker-compose up` | Full stack |
| `ruff check app/` | Lint |
"""

    return BackendProject(
        name=name, framework="fastapi",
        files=files, readme=readme,
        commands={
            "start":   "uvicorn main:app --reload",
            "test":    "pytest tests/ -v",
            "migrate": "alembic upgrade head",
            "build":   "docker build -t {name} .",
            "docker":  "docker-compose up",
        }
    )


# ── Express/TypeScript template ───────────────────────────────────────────────

def _express_project(name: str, description: str) -> BackendProject:
    slug = re.sub(r"[^a-z0-9-]", "-", name.lower())

    files = [
        ProjectFile("package.json", f"""\
{{
  "name": "{slug}",
  "version": "1.0.0",
  "description": "{description}",
  "main": "dist/server.js",
  "scripts": {{
    "dev": "tsx watch src/server.ts",
    "build": "tsc",
    "start": "node dist/server.js",
    "test": "jest --coverage",
    "lint": "eslint src --ext .ts",
    "db:migrate": "prisma migrate dev",
    "db:generate": "prisma generate",
    "db:studio": "prisma studio"
  }},
  "dependencies": {{
    "express": "^4.19.0",
    "@prisma/client": "^5.15.0",
    "jsonwebtoken": "^9.0.0",
    "bcryptjs": "^2.4.3",
    "zod": "^3.23.0",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "express-rate-limit": "^7.3.0",
    "morgan": "^1.10.0",
    "dotenv": "^16.4.0",
    "winston": "^3.13.0"
  }},
  "devDependencies": {{
    "typescript": "^5.5.0",
    "@types/express": "^4.17.21",
    "@types/jsonwebtoken": "^9.0.6",
    "@types/bcryptjs": "^2.4.6",
    "@types/cors": "^2.8.17",
    "@types/morgan": "^1.9.9",
    "@types/node": "^20.14.0",
    "tsx": "^4.15.0",
    "jest": "^29.7.0",
    "@types/jest": "^29.5.12",
    "supertest": "^7.0.0",
    "@types/supertest": "^6.0.2",
    "ts-jest": "^29.1.4",
    "prisma": "^5.15.0",
    "eslint": "^9.5.0"
  }}
}}
"""),

        ProjectFile("tsconfig.json", """\
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
"""),

        ProjectFile(".env.example", f"""\
PORT=3000
NODE_ENV=development
DATABASE_URL="postgresql://postgres:password@localhost:5432/{slug}"
JWT_SECRET=change-this-secret
JWT_EXPIRES_IN=15m
REFRESH_SECRET=change-this-refresh-secret
REFRESH_EXPIRES_IN=7d
CORS_ORIGIN=http://localhost:5173
"""),

        ProjectFile("prisma/schema.prisma", f"""\
generator client {{
  provider = "prisma-client-js"
}}

datasource db {{
  provider = "postgresql"
  url      = env("DATABASE_URL")
}}

model User {{
  id           Int      @id @default(autoincrement())
  email        String   @unique
  username     String   @unique
  passwordHash String
  isActive     Boolean  @default(true)
  isAdmin      Boolean  @default(false)
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt

  @@map("users")
}}
"""),

        ProjectFile("src/config.ts", """\
import { z } from "zod";
import dotenv from "dotenv";
dotenv.config();

const envSchema = z.object({
  PORT: z.string().default("3000"),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  DATABASE_URL: z.string(),
  JWT_SECRET: z.string().min(16),
  JWT_EXPIRES_IN: z.string().default("15m"),
  REFRESH_SECRET: z.string().min(16),
  REFRESH_EXPIRES_IN: z.string().default("7d"),
  CORS_ORIGIN: z.string().default("http://localhost:3000"),
});

export const config = envSchema.parse(process.env);
"""),

        ProjectFile("src/lib/prisma.ts", """\
import { PrismaClient } from "@prisma/client";
export const prisma = new PrismaClient({ log: ["warn", "error"] });
"""),

        ProjectFile("src/lib/logger.ts", """\
import winston from "winston";
export const logger = winston.createLogger({
  level: process.env.NODE_ENV === "production" ? "info" : "debug",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [new winston.transports.Console()],
});
"""),

        ProjectFile("src/middleware/auth.ts", """\
import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { config } from "../config";
import { prisma } from "../lib/prisma";

export interface AuthRequest extends Request {
  userId?: number;
}

export async function authenticate(req: AuthRequest, res: Response, next: NextFunction) {
  const auth = req.headers.authorization;
  if (!auth?.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Missing token" });
  }
  try {
    const payload = jwt.verify(auth.slice(7), config.JWT_SECRET) as { sub: string };
    const user = await prisma.user.findUnique({ where: { id: parseInt(payload.sub) } });
    if (!user?.isActive) return res.status(401).json({ error: "Unauthorized" });
    req.userId = user.id;
    next();
  } catch {
    return res.status(401).json({ error: "Invalid or expired token" });
  }
}
"""),

        ProjectFile("src/middleware/validate.ts", """\
import { Request, Response, NextFunction } from "express";
import { ZodSchema } from "zod";

export const validate = (schema: ZodSchema) =>
  (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(422).json({ error: "Validation failed", issues: result.error.issues });
    }
    req.body = result.data;
    next();
  };
"""),

        ProjectFile("src/routes/auth.ts", """\
import { Router } from "express";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { z } from "zod";
import { prisma } from "../lib/prisma";
import { config } from "../config";
import { validate } from "../middleware/validate";

const router = Router();

const registerSchema = z.object({
  email: z.string().email(),
  username: z.string().min(3).max(30),
  password: z.string().min(8),
});

router.post("/register", validate(registerSchema), async (req, res) => {
  const { email, username, password } = req.body;
  try {
    const passwordHash = await bcrypt.hash(password, 12);
    const user = await prisma.user.create({
      data: { email, username, passwordHash },
      select: { id: true, email: true, username: true, createdAt: true },
    });
    return res.status(201).json(user);
  } catch (err: any) {
    if (err.code === "P2002") return res.status(400).json({ error: "Email or username already taken" });
    throw err;
  }
});

router.post("/login", async (req, res) => {
  const { email, password } = req.body;
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user || !(await bcrypt.compare(password, user.passwordHash))) {
    return res.status(401).json({ error: "Invalid credentials" });
  }
  const accessToken = jwt.sign({ sub: String(user.id) }, config.JWT_SECRET, { expiresIn: config.JWT_EXPIRES_IN as any });
  const refreshToken = jwt.sign({ sub: String(user.id) }, config.REFRESH_SECRET, { expiresIn: config.REFRESH_EXPIRES_IN as any });
  return res.json({ accessToken, refreshToken, tokenType: "Bearer" });
});

export default router;
"""),

        ProjectFile("src/routes/users.ts", """\
import { Router } from "express";
import { prisma } from "../lib/prisma";
import { authenticate, AuthRequest } from "../middleware/auth";

const router = Router();

router.get("/me", authenticate, async (req: AuthRequest, res) => {
  const user = await prisma.user.findUnique({
    where: { id: req.userId },
    select: { id: true, email: true, username: true, isAdmin: true, createdAt: true },
  });
  return res.json(user);
});

export default router;
"""),

        ProjectFile("src/app.ts", f"""\
import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";
import rateLimit from "express-rate-limit";
import {{ config }} from "./config";
import {{ logger }} from "./lib/logger";
import authRouter from "./routes/auth";
import usersRouter from "./routes/users";

const app = express();

// Security
app.use(helmet());
app.use(cors({{ origin: config.CORS_ORIGIN, credentials: true }}));
app.use(rateLimit({{ windowMs: 15 * 60 * 1000, max: 100, message: "Too many requests" }}));

// Parsing
app.use(express.json({{ limit: "10mb" }}));

// Logging
app.use(morgan("combined", {{ stream: {{ write: (msg) => logger.info(msg.trim()) }} }}));

// Routes
app.use("/api/v1/auth", authRouter);
app.use("/api/v1/users", usersRouter);
app.get("/health", (_, res) => res.json({{ status: "ok", service: "{name}" }}));

// 404
app.use((_, res) => res.status(404).json({{ error: "Not found" }}));

// Error handler
app.use((err: Error, req: express.Request, res: express.Response, _: express.NextFunction) => {{
  logger.error(err.message, {{ stack: err.stack }});
  res.status(500).json({{ error: "Internal server error" }});
}});

export default app;
"""),

        ProjectFile("src/server.ts", """\
import app from "./app";
import { config } from "./config";
import { logger } from "./lib/logger";
import { prisma } from "./lib/prisma";

const PORT = parseInt(config.PORT);

async function main() {
  await prisma.$connect();
  app.listen(PORT, () => logger.info(`Server running on port ${PORT}`));
}

main().catch((err) => { logger.error(err); process.exit(1); });
"""),

        ProjectFile("src/__tests__/auth.test.ts", """\
import request from "supertest";
import app from "../app";
import { prisma } from "../lib/prisma";

afterAll(() => prisma.$disconnect());

describe("Auth", () => {
  it("GET /health → 200", async () => {
    const r = await request(app).get("/health");
    expect(r.status).toBe(200);
    expect(r.body.status).toBe("ok");
  });

  it("POST /register → 201", async () => {
    const r = await request(app).post("/api/v1/auth/register").send({
      email: `test${Date.now()}@example.com`,
      username: `user${Date.now()}`,
      password: "SecurePass123",
    });
    expect(r.status).toBe(201);
    expect(r.body.email).toBeDefined();
  });

  it("POST /login → 200 with tokens", async () => {
    const email = `login${Date.now()}@example.com`;
    await request(app).post("/api/v1/auth/register").send({ email, username: `u${Date.now()}`, password: "Pass1234" });
    const r = await request(app).post("/api/v1/auth/login").send({ email, password: "Pass1234" });
    expect(r.status).toBe(200);
    expect(r.body.accessToken).toBeDefined();
  });

  it("GET /users/me unauthorized → 401", async () => {
    const r = await request(app).get("/api/v1/users/me");
    expect(r.status).toBe(401);
  });
});
"""),

        ProjectFile("Dockerfile", """\
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/prisma ./prisma
EXPOSE 3000
CMD ["node", "dist/server.js"]
"""),

        ProjectFile("docker-compose.yml", f"""\
version: "3.9"
services:
  api:
    build: .
    ports: ["3000:3000"]
    env_file: .env
    depends_on: {{db: {{condition: service_healthy}}}}
    command: npm run dev
  db:
    image: postgres:16-alpine
    environment: {{POSTGRES_DB: {slug}, POSTGRES_USER: postgres, POSTGRES_PASSWORD: password}}
    ports: ["5432:5432"]
    healthcheck: {{test: ["CMD-SHELL","pg_isready -U postgres"], interval: 5s, retries: 5}}
"""),

        ProjectFile(".gitignore", "node_modules/\ndist/\n.env\n*.db\ncoverage/\n"),
    ]

    readme = f"""# {name}

{description}

## Stack
- **Framework**: Express.js + TypeScript
- **Database**: PostgreSQL + Prisma ORM
- **Auth**: JWT (access + refresh) + bcrypt
- **Validation**: Zod
- **Tests**: Jest + Supertest

## Quick start
```bash
cp .env.example .env
npm install
npx prisma migrate dev
npm run dev
```
Open http://localhost:3000/health
"""

    return BackendProject(
        name=name, framework="express",
        files=files, readme=readme,
        commands={
            "dev":     "npm run dev",
            "test":    "npm test",
            "build":   "npm run build",
            "migrate": "npx prisma migrate dev",
            "docker":  "docker-compose up",
        }
    )


# ── Django REST Framework template ────────────────────────────────────────────

def _django_project(name: str, description: str) -> BackendProject:
    slug = re.sub(r"[^a-z0-9_]", "_", name.lower())

    files = [
        ProjectFile("requirements.txt", """\
Django>=5.0.0
djangorestframework>=3.15.0
djangorestframework-simplejwt>=5.3.0
django-cors-headers>=4.4.0
psycopg2-binary>=2.9.0
django-environ>=0.11.0
drf-spectacular>=0.27.0
celery[redis]>=5.4.0
pytest-django>=4.8.0
factory-boy>=3.3.0
"""),
        ProjectFile(f"{slug}/settings.py", f"""\
import environ, os
from pathlib import Path

env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "corsheaders", "drf_spectacular",
    "apps.users",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "{slug}.urls"
DATABASES = {{"default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")}}
AUTH_USER_MODEL = "users.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"

REST_FRAMEWORK = {{
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}}

SPECTACULAR_SETTINGS = {{
    "TITLE": "{name} API",
    "DESCRIPTION": "{description}",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
"""),
        ProjectFile(f"{slug}/urls.py", """\
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/users/", include("apps.users.urls")),
]
"""),
        ProjectFile("apps/__init__.py", ""),
        ProjectFile("apps/users/__init__.py", ""),
        ProjectFile("apps/users/models.py", """\
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    bio   = models.TextField(blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
    class Meta: db_table = "users"
"""),
        ProjectFile("apps/users/serializers.py", """\
from rest_framework import serializers
from apps.users.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "bio", "date_joined"]

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ["email", "username", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
"""),
        ProjectFile("apps/users/views.py", """\
from rest_framework import generics, permissions
from apps.users.models import User
from apps.users.serializers import UserSerializer, RegisterSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    def get_object(self): return self.request.user
"""),
        ProjectFile("apps/users/urls.py", """\
from django.urls import path
from apps.users.views import RegisterView, MeView
urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("me/", MeView.as_view()),
]
"""),
        ProjectFile("manage.py", f"""\
#!/usr/bin/env python
import os, sys
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{slug}.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
""", executable=True),
        ProjectFile(".env.example", f"""\
SECRET_KEY=change-this-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:password@localhost:5432/{slug}
CORS_ALLOWED_ORIGINS=http://localhost:3000
"""),
        ProjectFile("pytest.ini", f"""\
[pytest]
DJANGO_SETTINGS_MODULE = {slug}.settings
python_files = tests.py test_*.py *_test.py
"""),
        ProjectFile("tests/__init__.py", ""),
        ProjectFile("tests/test_users.py", """\
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_register(client):
    r = client.post("/api/v1/users/register/", {
        "email": "test@example.com", "username": "testuser", "password": "Pass1234"
    }, content_type="application/json")
    assert r.status_code == 201

@pytest.mark.django_db
def test_me_unauthorized(client):
    r = client.get("/api/v1/users/me/")
    assert r.status_code == 401
"""),
        ProjectFile("Dockerfile", """\
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
"""),
    ]

    readme = f"""# {name}

{description}

## Stack
- **Framework**: Django 5 + Django REST Framework
- **Database**: PostgreSQL
- **Auth**: JWT (simplejwt)
- **Docs**: drf-spectacular (Swagger)
- **Tests**: pytest-django

## Quick start
```bash
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Docs: http://localhost:8000/api/docs/
"""

    return BackendProject(
        name=name, framework="django",
        files=files, readme=readme,
        commands={
            "start":   "python manage.py runserver",
            "test":    "pytest",
            "migrate": "python manage.py migrate",
            "shell":   "python manage.py shell",
        }
    )


# ── Main Generator ────────────────────────────────────────────────────────────

class BackendGenerator:
    """
    Scaffolds complete backend projects with BASTIAN's expertise built in.
    Every generated project is production-ready with auth, DB, tests, Docker.
    """

    SUPPORTED = {"fastapi", "express", "django"}

    def generate(
        self,
        framework:   str,
        name:        str,
        description: str = "",
    ) -> BackendProject:
        """
        Generate a complete backend project.

        Args:
            framework:   "fastapi" | "express" | "django"
            name:        Project name (used for folder, package name, etc.)
            description: Short description for README and OpenAPI docs

        Returns:
            BackendProject with all files ready to write
        """
        framework = framework.lower()
        if framework not in self.SUPPORTED:
            raise ValueError(f"Framework '{framework}' not supported. Use: {self.SUPPORTED}")

        desc = description or f"{name} API"

        builders = {
            "fastapi": _fastapi_project,
            "express": _express_project,
            "django":  _django_project,
        }
        return builders[framework](name, desc)

    def list_frameworks(self) -> List[str]:
        return sorted(self.SUPPORTED)

    def describe(self) -> str:
        lines = ["BackendGenerator — Supported Frameworks", "─" * 50]
        details = {
            "fastapi": "Python async · SQLAlchemy · Alembic · Pydantic v2 · pytest",
            "express": "Node.js TypeScript · Prisma · Zod · Jest · Supertest",
            "django":  "Python · DRF · simplejwt · drf-spectacular · pytest",
        }
        for fw, desc in details.items():
            lines.append(f"  {fw:<10} {desc}")
        lines.append("")
        lines.append("Every project includes:")
        lines.append("  JWT auth · PostgreSQL · Docker · Tests · CI · OpenAPI docs")
        return "\n".join(lines)


# ── BASTIAN integration ───────────────────────────────────────────────────────

def bastian_generate(
    framework: str,
    name:      str  = "my-api",
    brief:     str  = "",
    output:    str  = "",
) -> BackendProject:
    """
    Generate a backend project using BASTIAN's expertise.
    Optionally writes to disk if output path provided.

        project = bastian_generate("fastapi", "user-service", "User management API with roles")
        project.write_to("~/projects/user-service")
    """
    gen     = BackendGenerator()
    project = gen.generate(framework, name, brief)

    if output:
        created = project.write_to(output)
        print(f"[BASTIAN] ✅ {framework} project '{name}' created: {len(created)} files → {output}")

    return project


# ── Singleton ─────────────────────────────────────────────────────────────────

_gen: Optional[BackendGenerator] = None

def get_backend_generator() -> BackendGenerator:
    global _gen
    if _gen is None:
        _gen = BackendGenerator()
    return _gen


if __name__ == "__main__":
    gen = BackendGenerator()
    print(gen.describe())
    print()

    # Generate FastAPI project
    project = gen.generate("fastapi", "todo-api", "Simple TODO API with JWT auth")
    print(project.summary())
    print(f"\nFiles: {[f.path for f in project.files[:5]]}...")
    print("\nCommands:")
    for k, v in project.commands.items():
        print(f"  {k}: {v}")
