# Usage Event API with Charge Preview

A REST API built with Python, FastAPI, PostgreSQL, SQLAlchemy, and JWT authentication. It accepts usage events, prevents duplicate event storage, and calculates charge previews for voice, SMS, and data usage.

## Features

- Customer registration and login using JWT authentication.
- Password hashing.
- Usage event ingestion for single events and bulk lists.
- Event validation using Pydantic.
- Filtering events by type and timestamp range.
- Charge previews grouped by voice, SMS, and data.
- Idempotent event ingestion using unique event IDs and PostgreSQL conflict handling.
- Database schema migrations using Alembic.
- Docker Compose setup for the API and PostgreSQL.
- Automated API tests using pytest.

## Technology Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT
- Docker Compose
- Pytest

## Run the Project

### Prerequisites

Install Docker Desktop and ensure Docker is running.

### Start the API and database

```bash
docker compose up --build -d
```

The API will be available at:

- API: http://localhost:8000
- Interactive Swagger documentation: http://localhost:8000/docs

### Stop the services

```bash
docker compose down
```

### View application logs

```bash
docker compose logs -f app
```

## Authentication

### Register a customer

`POST /register`

Example request:

```json
{
  "name": "Test Customer",
  "email": "customer@example.com",
  "password": "StrongPassword123"
}
```

### Log in

`POST /login`

Submit the email as the `username` form field and the password as the `password` form field. The API returns a JWT access token.

Use the token as a Bearer token for protected endpoints. In Swagger, click **Authorize** and enter your login credentials.

## Usage Events

### Submit one event

`POST /events`

```json
{
  "event_id": "event-001",
  "customer_id": 1,
  "event_type": "voice",
  "quantity": 10,
  "timestamp": "2026-10-22T10:00:00Z"
}
```

### Submit multiple events

`POST /events`

Send a JSON array containing usage events. Each event must have a unique event ID for it to be stored as a new event.

The response reports how many events were received, stored, and ignored as duplicates.

### Retrieve events

`GET /events`

Optional filters:

- `customer_id`
- `event_type` (`voice`, `sms`, or `data`)
- `from`
- `to`

Customers can access only their own usage events.

## Charge Preview

`GET /customers/{customer_id}/charge-preview?from=...&to=...`

Returns usage quantities and charges for voice, SMS, and data, along with the total charge for the selected time range.

The default sample rate plan uses:

- Voice: 2.00 per unit
- SMS: 3.00 per unit
- Data: 1.00 per unit

These are sample rates and can be changed in the rate plan configuration.

## Database Migrations

Alembic manages database schema changes. Migrations are applied automatically when the Docker application starts.

To apply migrations manually from an appropriately configured environment:

```bash
alembic upgrade head
```

## Tests

Run the automated tests in an environment with the required Python packages and a configured test database:

```bash
python -m pytest tests/test_api.py -v
```

The test suite covers authentication, registration and login, duplicate event handling, and charge preview calculation.

## How do you guarantee idempotency?

Each usage event has a unique `event_id`, enforced by a unique constraint in PostgreSQL. Event ingestion uses PostgreSQL's `INSERT ... ON CONFLICT DO NOTHING`. If an event with the same ID has already been stored, a repeated request does not insert it again.

The uniqueness constraint is enforced by the database, so concurrent requests attempting to insert the same event cannot both create separate rows. The API reports duplicates as ignored events.

## What would break at 10,000 events per second, and what would you change?

At 10,000 events per second, the API's request processing, database connections, indexes, and PostgreSQL write capacity could become bottlenecks. Bulk requests and synchronous database writes may increase latency, while database contention and connection exhaustion could reduce throughput.

I would load-test the system and measure API latency, database write latency, connection-pool usage, and error rates. I would then consider:

1. Adding a durable message broker such as Kafka between ingestion and database processing.
2. Scaling ingestion workers horizontally and using controlled batching.
3. Optimizing indexes and database connection pooling.
4. Partitioning the usage-event table by time or another suitable key when justified by query patterns.
5. Adding monitoring, retry handling, dead-letter processing, and backpressure.
6. Keeping event IDs unique and preserving idempotent processing across retries.

These changes would need to be validated through load testing and operational monitoring before claiming the system can sustain 10,000 events per second.
