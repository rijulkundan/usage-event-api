# Usage Event API

This is a Python API project built using FastAPI and PostgreSQL. It is used to store customer usage events for voice, SMS, and data and calculate the charges for that usage.

I built this project as part of a backend assignment. It includes user authentication, event handling, charge preview, and basic tests.

## Technologies Used

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic for database migrations
- JWT for authentication
- Docker and Docker Compose
- Pytest for testing

## Features

- Register a customer and log in using email and password.
- Use a JWT token to access protected APIs.
- Add a single usage event or multiple events in one request.
- Get usage events by customer, event type, and date range.
- Calculate voice, SMS, and data charges for a selected period.
- Ignore duplicate events using a unique event ID.
- Validate request data and return errors for invalid requests.

## How to Run the Project

Make sure Docker Desktop is installed and running.

Clone the repository:

```bash
git clone https://github.com/rijulkundan/usage-event-api.git
cd usage-event-api
```

Start the application:

```bash
docker compose up --build
```

The API will be available at:

`http://localhost:8000`

You can test the endpoints using Swagger:

`http://localhost:8000/docs`

The database migrations run when the application starts.

## Authentication

First, register a customer using `POST /register`.

Then log in using `POST /login` to get an access token. Use this token to call the protected endpoints.

The login endpoint accepts the email in the `username` field and the password in the form data.

## Adding Usage Events

The `POST /events` endpoint accepts a single event or a list of events.

Example:

```json
{
  "event_id": "event-101",
  "customer_id": 1,
  "event_type": "voice",
  "quantity": 10,
  "timestamp": "2026-10-22T10:00:00Z"
}
```

The event type can be `voice`, `sms`, or `data`. The quantity must be greater than zero.

You must be logged in, and you can only submit events for your own customer account.

## Getting Usage Events

Use `GET /events` to retrieve events. You can filter the results using the customer ID, event type, and date range.

For example:

`GET /events?event_type=voice`

You can also use the `from` and `to` query parameters to filter events by date.

## Charge Preview

Use the following endpoint to calculate charges for a customer over a selected period:

`GET /customers/{customer_id}/charge-preview?from=2026-10-01T00:00:00Z&to=2026-11-01T00:00:00Z`

The response contains the total quantity and charge for voice, SMS, and data, along with the overall charge.

The default rate plan uses these rates:

| Usage type | Price per unit |
|---|---:|
| Voice | 2.00 |
| SMS | 3.00 |
| Data | 1.00 |

These are sample rates for this project.

## How Duplicate Events Are Handled

Each event has a unique `event_id` in the database.

When an event is submitted, the API uses PostgreSQL's `ON CONFLICT DO NOTHING` to skip an event if that ID already exists. This also helps prevent duplicate records when two requests try to insert the same event at the same time.

The API returns how many events were received, how many were stored, and how many duplicates were ignored.

## Database Migrations

Alembic is used to manage changes to the database tables.

The migrations are stored in the `migrations/` folder and run automatically when the application starts through Docker Compose.

## Running the Tests

Run the following commands in your local Python environment:

```bash
python -m pytest tests/test_api.py -v
```

The tests cover authentication, access without a valid token, duplicate event handling, and charge preview calculation.

## What Could Break at 10,000 Events per Second?

At this rate, the API and PostgreSQL database could become bottlenecks. Too many simultaneous database writes and limited database connections could slow down requests.

I would first test the application under heavy load and check response times, database performance, and connection usage.

If more capacity is needed, I would add Kafka to buffer incoming events and process them using multiple workers. I would also look at batching database writes, improving indexes, and scaling the application horizontally. I would make sure retries do not create duplicate events and add monitoring to track failures and processing delays.
