# FitTrack Pro ![Coverage](coverage.svg)

Smart Workout, Nutrition & Progress Manager — built for HealthHub.

## Stack

- Python 3.11, Flask 2.x, SQLAlchemy 2, PostgreSQL 15
- React-Vite PWA
- Docker + GitHub Actions CI

## Docker First

```bash
# 1. Build and start the full app stack
docker compose up -d --build

# 2. Seed demo data into the Docker database
docker compose exec api python seed.py --reset

# 3. Check the running services
docker compose ps
```

Accessible URLs:

- API hub: `http://localhost:5000/`
- API health: `http://localhost:5000/health`
- React PWA: `http://localhost:4173/`
- PostgreSQL: `localhost:15432`

The Docker stack now builds and serves the PWA inside Docker, so no local `npm install`, `npm run build`, or host Python setup is required to run the app.

## Local Development

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Start only the database in Docker
docker compose up -d db

# 3. Point local scripts at the Docker database
$env:DATABASE_URL="postgresql://fittrack:fittrack123@localhost:15432/fittrackdb"

# 4. Seed sample data
python seed.py

# 5. Run the API
python app.py
```

The API will be available at `http://localhost:5000`.
The Docker database is published on `localhost:15432` by default to avoid Windows-reserved port conflicts on `5432`.

## React PWA

Docker usage:

```bash
docker compose up -d --build pwa
```

Local frontend-only development:

```bash
cd pwa
npm install
npm run dev
```

The PWA is available at `http://localhost:4173` in both flows and talks to the Flask API at `http://localhost:5000` by default.

## Seed CLI

Docker usage:

```bash
# full demo dataset
docker compose exec api python seed.py

# only workout history
docker compose exec api python seed.py --dataset exercises --days 14 --reset

# only food history
docker compose exec api python seed.py --dataset foods --days 5 --reset
```

Local usage:

```bash
python seed.py
python seed.py --dataset exercises --days 14 --reset
python seed.py --dataset foods --days 5 --reset
```

The helper keeps the demo coach and user accounts available and can reset existing seeded data before replaying a dataset.

## Running Tests

```bash
pytest
```

Coverage report is printed to the terminal. Must stay above 80%.

PWA smoke tests:

```bash
cd pwa
npm test
```

Docker smoke tests for the current running stack:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:4173/
```

## CI

GitHub Actions now runs Python linting and tests, builds the React PWA, pushes the Docker image on `main`, uploads `coverage.xml` to Codecov, and generates a `coverage.svg` badge artifact.

## Environment Variables

Create a `.env` file and fill in your values:

```
DATABASE_URL=postgresql://fittrack:fittrack123@localhost:15432/fittrackdb
JWT_SECRET_KEY=your-secret-key
NUTRITION_API_KEY=your-nutritionix-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your-app-password
```

## Project Structure

```
fittrack/
├── domain/
│   ├── entities/       # User, WorkoutSession, MealEntry, etc.
│   └── services/       # CalorieCalculator, ProgressAnalyser, BadgeChecker
├── ports/              # Abstract repository and service interfaces
├── adapters/
│   ├── db/             # SQLAlchemy models + PostgreSQL repositories
│   ├── api/            # Flask routes + report generator
│   ├── nutrition/      # Nutritionix API adapter with cache fallback
│   └── notifications/  # Email notification adapter
├── tests/
│   ├── unit/           # Domain logic tests
│   ├── integration/    # API endpoint tests
├── config/             # Settings and environment config
├── seed.py             # CLI tool to populate dev database
└── app.py              # Entry point
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/register | Create account |
| POST | /auth/login | Get JWT token |
| POST | /workouts | Log a workout session |
| GET | /workouts/{user_id} | Get user's workout history |
| POST | /meals | Log a meal entry |
| POST | /meals/sync | Sync offline-queued meals |
| GET | /meals/search?q= | Search food nutrition data |
| POST | /users/{id}/measurements | Record body measurement |
| POST | /users/{id}/goals | Set a fitness goal |
| GET | /users/{id}/progress | Get progress report (JSON) |
| GET | /coach/dashboard | Coach client list |
| GET | /coach/clients/{id}/progress?format=csv | Export CSV report |
| GET | /coach/clients/{id}/progress?format=pdf | Export PDF report |

## Demo Accounts (after seeding)

- Coach: `coach@fittrack.com` / `coach123`
- User: `user@fittrack.com` / `user123`
