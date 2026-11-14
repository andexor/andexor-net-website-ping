# Andexor Ping Service

This service logs clicks on the website.

Links on https://andexor.net/ list `https://andexor.net/api/v1/ping` in their `ping` attribute.
The browser sends a POST to this Cloudflare Worker (Python, FastAPI) whenever a visitor clicks one.
The Worker logs the request headers and writes a row to a D1 database, so that interactive use
can be told apart from non-interactive use.

## Quick start

See [setup.md](./setup.md) for pre-requisites, creating the databases, running, deploying, and testing.

## Documentation

See the following documents to get started:

- [Setup](./setup.md)
- [Prompt](./prompt.md)
- [Product Requirements Document](./PRD.md)
- [CI/CD Pipeline Setup](./CICD.md)
