# SHAKSHAM — Adaptive Fitness Platform

Fitness that adapts to the user, not the other way around.
Built with **HTML + CSS + vanilla JS** (frontend), **Python Flask** (backend) and **SQLite / SQL** (database).

> SHAKSHAM gives general fitness guidance only. It does not diagnose, treat or replace professional medical advice.

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

The database (`instance/shaksham.db`) is created and seeded automatically on first run.

**Demo login:** `demo@shaksham.app` / `Demo@1234`

## Flow
Home → Register/Login → 5-step Assessment → Safety gate → Personalised routine → Guided workout → "How did this feel?" → Dashboard / Progress / Achievements

## Pages
| Route | Purpose |
|---|---|
| `/` | Landing page |
| `/register`, `/login` | Auth (hashed passwords, Flask sessions, CSRF token) |
| `/assessment` | 5 small steps with review/edit before submit |
| `/dashboard` | Today's workout, streak, weekly chart, goals, recent feedback |
| `/exercises`, `/exercise/<slug>` | Filterable library and detail pages |
| `/workout/<plan_id>` | Guided player: timer/reps, pause, next, stop, feedback |
| `/progress`, `/achievements`, `/profile` | History, milestones, accessibility settings |

## How recommendations work (rule-based, no black box)
`logic/recommendation.py` → `logic/workout_generator.py`
1. Remove exercises needing equipment you don't have
2. Remove exercises marked to avoid for your reported limitations (and unsuitable positions, e.g. no unsupported standing moves with balance difficulty)
3. Cap difficulty by experience, limitations and fatigue
4. Prefer exercises matching your goal, covering different body areas
5. Fit warm-up + main + cool-down into your chosen time
6. Show a plain-English "why" for every exercise

## Safety gate (`logic/safety_checker.py`)
If the user reports chest pain, fainting, severe breathlessness, severe/sudden pain, a recent serious injury, or a professional restriction on exercise, **no workout is generated**; a safety message is shown instead. Choosing **pain / unusual symptoms** during a workout stops the session immediately and never auto-progresses.

## Database (`database/schema.sql`)
users, assessments, exercises, workout_plans, workout_exercises, workout_sessions, exercise_feedback, achievements, user_achievements.

## Accessibility
Semantic HTML, skip link, keyboard-friendly large controls, visible focus, labelled inputs, ARIA live regions, text alternatives for exercise illustrations, status shown with text/symbols (not colour alone), high-contrast mode, text size options, reduced-motion support.

## Tests
```bash
python -m unittest discover -s tests -t .
```

## Notes / next steps
- Exercise content must be reviewed by a qualified fitness/health professional before real use.
- `media_url` on each exercise is ready for real images/videos (currently simple SVG placeholders).
- Set a real `SECRET_KEY` environment variable before deploying anywhere public.
