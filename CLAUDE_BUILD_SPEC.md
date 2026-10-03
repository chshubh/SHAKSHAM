# SHAKSHAM — Build Specification for Claude

You are building a complete full-stack Flask web application called SHAKSHAM.

## Product goal
Create an adaptive fitness website that helps users select and perform exercises based on:
- current physical ability
- stated limitations
- health/safety responses
- fitness experience
- goal
- available equipment
- available time

It must also work for users without major limitations.

## Critical safety behavior
This is a fitness guidance product, not a medical product.

Never:
- diagnose a condition
- claim an exercise cures a disease/injury
- guarantee medical outcomes
- automatically prescribe exercises based only on a condition name
- tell a user to exercise through significant pain or alarming symptoms

Include a clear disclaimer that the platform does not replace professional medical advice.

Create a safety gate. If a user reports red-flag symptoms or a professional has specifically restricted exercise, do not generate a normal workout. Show a safety message recommending appropriate professional guidance.

Potential red-flag examples for the screening logic:
- chest pain during activity
- fainting or near-fainting
- severe unexplained shortness of breath
- recent serious injury
- severe acute pain
- explicit professional instruction to avoid exercise

These are examples for conservative software behavior, not a diagnostic checklist.

## Assessment UX

Break the assessment into small steps.

Step 1: Basic profile
- age group
- fitness experience
- normal activity level
- preferred workout duration
- equipment

Step 2: Goal
- general fitness
- mobility
- strength
- flexibility
- balance
- endurance

Step 3: Current physical ability
- walking difficulty
- standing difficulty
- upper-body movement limitation
- lower-body movement limitation
- balance difficulty
- flexibility limitation
- fatigue with activity
- none

Step 4: Health/safety
- current health status
- current injury/recovery status
- diagnosed conditions (optional, user-entered categories only)
- symptoms relevant to exercise safety
- professional exercise restrictions

Step 5: Confirmation
- explain that answers are used for general personalization
- show disclaimer
- allow user to edit answers

## Recommendation engine

Implement a transparent rule-based engine first.

Inputs:
- goal
- difficulty/experience
- limitations
- equipment
- available time
- safety status

Pipeline:
1. Load exercises
2. Remove exercises incompatible with equipment
3. Remove exercises incompatible with known user limitations
4. Apply difficulty filter
5. Match goal/category
6. Match available time
7. Build a balanced routine
8. Return explanation for why exercises were selected

Do not use black-box AI for the first version.

## Exercise data

Each exercise should support:
- id
- name
- category
- difficulty
- equipment
- position
- target_area
- duration_seconds
- default_sets
- default_reps
- instructions
- breathing_tip
- common_modifications
- safety_notes
- suitable_for
- avoid_if
- media_url (optional)

Exercise information must be treated as content that should eventually be reviewed by a qualified fitness/health professional.

## Guided workout

For every exercise display:
- exercise name
- visual/media placeholder
- current step
- timer or reps
- instructions
- pause
- next
- stop
- "How did this feel?"

Feedback:
- easy
- moderate
- difficult
- pain/unusual symptoms

If pain/unusual symptoms is selected, stop the session and show a safety-oriented message rather than automatically progressing.

## Dashboard

Show only useful information:
- today's recommended workout
- duration
- completed sessions
- active days/streak
- weekly activity
- current goals
- recent feedback
- progress charts

## Accessibility
Implement:
- semantic HTML
- keyboard navigation
- visible focus states
- sufficient color contrast
- large buttons
- reduced-motion preference
- responsive layout
- labels for form controls
- aria attributes where appropriate
- text alternatives for exercise media
- avoid relying on color alone

## Pages/routes

GET:
/
 /login
 /register
 /assessment
 /dashboard
 /exercises
 /exercise/<id>
 /workout/<id>
 /progress
 /achievements
 /profile

POST:
 /login
 /register
 /assessment
 /workout/<id>/complete
 /workout/<id>/feedback
 /profile

## Database models

Create:
User
Assessment
Exercise
WorkoutPlan
WorkoutExercise
WorkoutSession
ExerciseFeedback
Achievement
UserAchievement

Keep the schema simple and understandable.

## Authentication
Use Flask sessions and password hashing. Never store plaintext passwords.

## Visual style
Suggested palette:
- deep navy/charcoal background
- white/off-white surfaces
- accessible blue/teal accent
- green for completed/success
- amber for caution
- red only for safety warnings

Use cards, progress bars and clean spacing. Avoid excessive gradients and animations.

## Development priority
Build a functional MVP first:
Home → Auth → Assessment → Recommendation → Exercise Detail → Workout → Feedback → Dashboard.

Then add:
Progress → Achievements → Accessibility settings → richer media.

## Deliverable
The resulting project must run locally with:
python -m venv venv
pip install -r requirements.txt
python app.py

Provide clear setup instructions and seed demo data.
