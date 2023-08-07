# Prerequisites

Before you begin, ensure you have the following installed:

- Docker
- Docker Compose (usually included with Docker Desktop)

You can find installation instructions at https://docs.docker.com/engine/install/.

Getting Started
Follow these steps to get your project up and running.

# Development Setup

Clone this repository to your local machine:

    git clone https://github.com/yourusername/your-django-docker-project.git
    cd your-django-docker-project

Create a copy of the .env.example file and name it .env. Update the environment variables as needed.

Build the Docker containers and start the development server:

    docker-compose -f docker-compose.dev.yml up -d --build

Access the application at http://localhost:8000.
