# MangaDex Clone

This is a web application that clones core features of MangaDex, a popular manga reading platform. Built with Flask, it allows users to browse, search, and manage manga titles, create reading lists, comment on series, and more. The project includes user authentication, an admin panel, and integration with the MangaDex API for fetching manga data.

## Features

- **User Authentication**: Register, login, and profile management.
- **Manga Browsing**: Home page with recently added, popular, and seasonal manga.
- **Advanced Search**: Filter manga by tags, genres, demographics, and more.
- **Manga Details**: View chapters, covers, ratings, and related content.
- **Reading Lists (MDLists)**: Create public/private lists, follow others' lists, add/remove manga.
- **Comments**: Post and manage comments on manga pages.
- **Admin Panel**: Manage users, manga, creators, and comments (for admins).
- **Reader Mode**: Basic manga chapter reader.
- **Dashboard**: User-specific updates and recommendations.
- **API Integration**: Fetches data from MangaDex API for covers and details.

## Tech Stack

- **Backend**: Python 3, Flask, SQLAlchemy (for ORM and database management).
- **Database**: SQLite (default; can be configured for PostgreSQL/MySQL).
- **Frontend**: Jinja2 templates, Bootstrap 5, custom CSS/JS for UI.
- **Other**: Flask-Login for auth, Requests for API calls, UUID for IDs.

## Prerequisites

- Python 3.8+
- Virtualenv (recommended)
- A MangaDex API key (optional for full features; set in config).

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/mini-demo.git
   cd mini-demo
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies (create `requirements.txt` if not present):
   ```
   pip install flask flask-login flask-sqlalchemy requests uuid base64
   ```

4. Set up the database:
   - Run `flask db init` if using Flask-Migrate (optional).
   - Or manually create tables via `models.py`.

5. Configure environment variables (in `.env` or directly in `__init__.py`):
   - `SECRET_KEY=your_secret_key`
   - `SQLALCHEMY_DATABASE_URI=sqlite:///site.db`

## Running the Application

1. Start the server:
   ```
   python run.py
   ```

2. Open in browser: http://127.0.0.1:5000

- Default admin credentials: Check `auth.py` or seed script.
- Register a new user to explore features.

## Project Structure

- `app/`: Core application code.
  - `__init__.py`: App initialization, blueprints, DB config.
  - `models.py`: SQLAlchemy models (User, Manga, List, etc.).
  - `routes.py`: Main routes (home, search, etc.).
  - `list_routes.py`: MDList management API.
  - `templates/`: Jinja2 HTML files (base.html, manga_detail.html, etc.).
  - `static/`: CSS, JS, assets (images, icons).
- `run.py`: Entry point to run the app.

## Contributing

- Fork the repo.
- Create a feature branch: `git checkout -b feature/new-feature`.
- Commit changes: `git commit -m 'Add new feature'`.
- Push: `git push origin feature/new-feature`.
- Open a Pull Request.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by MangaDex.
- Uses MangaDex API for data fetching (respect rate limits).