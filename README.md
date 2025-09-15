# Little Automation Tool

A Django-based automation tool with PostgreSQL, ready for containerized development.

## Requirements

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

## Getting Started

### 1. Clone the repository

```sh
git clone https://github.com/Pratamartin/little_automation_tool.git
cd gp_automation_tool
```

### 2. Configure environment variables

Copy the example environment file and edit as needed:

```sh
cp dotenv_files/.env-example dotenv_files/.env
```

Edit `dotenv_files/.env` to set your secrets and database credentials.

### 3. Build and start the containers

```sh
docker-compose up --build
```

This will:

- Build the Django and PostgreSQL containers
- Run database migrations
- Collect static files
- Start the Django development server at [http://localhost:8000](http://localhost:8000)

### 4. Access the application

- Django app: [http://localhost:8000](http://localhost:8000)
- Admin panel: [http://localhost:8000/admin/](http://localhost:8000/admin/)

### 5. Stopping the application

Press `Ctrl+C` in your terminal, then run:

```sh
docker-compose down
```

## Development

- App code is in [`djangoapp/`](djangoapp/)
- Static and media files are stored in [`data/web/static/`](data/web/static/) and [`data/web/media/`](data/web/media/)
- Database data is persisted in [`data/postgres/data/`](data/postgres/data/)

## Useful Commands

- Run Django management commands inside the container:

  ```sh
  docker-compose exec djangoapp python manage.py <command>
  ```

