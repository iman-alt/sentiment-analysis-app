# SentimentLab — Full-Stack Sentiment Analysis Web App

A Flask web application with full user authentication that lets users sign up, log in, analyze the sentiment of any text using VADER, and track their analysis history over time with interactive charts.

## Features

- Secure user signup/login with hashed passwords (Werkzeug)
- Session-based authentication
- Real-time sentiment analysis using VADER (positive/neutral/negative/compound scores)
- Interactive charts (Chart.js) — doughnut chart per analysis, line chart for history trends
- SQLite database storing users and their analysis history
- Vibrant, custom-designed UI

## Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLite
- **Auth:** Werkzeug password hashing + Flask sessions
- **Sentiment Engine:** VADER (vaderSentiment)
- **Charts:** Chart.js
- **Frontend:** HTML, CSS (no framework)

## How Authentication Works

1. On signup, the password is hashed with `generate_password_hash()` before being stored — the plain password is never saved.
2. On login, the typed password is checked against the stored hash with `check_password_hash()`.
3. On success, Flask stores the user's ID in an encrypted session cookie.
4. Protected routes (dashboard, history) use a `@login_required` decorator that checks for a valid session before allowing access.

## Setup

```bash
git clone https://github.com/iman-alt/sentiment-analysis-app.git
cd sentiment-analysis-app
pip install -r requirements.txt
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.

## Database Schema

**users**
| Column | Type |
|---|---|
| id | INTEGER PK |
| username | TEXT UNIQUE |
| password_hash | TEXT |
| created_at | TEXT |

**analyses**
| Column | Type |
|---|---|
| id | INTEGER PK |
| user_id | INTEGER FK |
| text | TEXT |
| positive / neutral / negative / compound | REAL |
| label | TEXT |
| created_at | TEXT |

## Project Structure
sentiment-analysis-app/
├── app.py
├── requirements.txt
├── templates/
└── static/

## License

MIT
