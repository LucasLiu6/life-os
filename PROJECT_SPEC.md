# Life OS — Proactive Personal Chief of Staff

## 1. Product Goal

Life OS is a proactive personal Chief of Staff for one user.

It is not a passive chatbot. Its job is to help the user stay on track across academics, internship recruiting, skill learning, health/soccer, and life admin.

The assistant should proactively:
- create daily plans
- check in every evening
- run weekly reviews
- track long-term goals
- track short-term tasks
- notice when the user is falling behind
- suggest realistic next actions
- remember progress over time

## 2. Core Principle

The assistant should help the user succeed in real life.

It should be:
- proactive
- practical
- honest
- supportive
- accountability-focused
- privacy-conscious
- safe around irreversible actions

The assistant should not just answer questions. It should manage loops:
- morning planning loop
- evening check-in loop
- weekly review loop
- goal progress loop
- task follow-up loop

## 3. V1 Scope

V1 should only include the core proactive life management system.

V1 includes:
- Telegram chat interface
- backend server
- database
- goals table
- tasks table
- daily check-ins table
- agent run logs
- morning briefing generation
- evening check-in generation
- weekly review generation
- scheduler for proactive messages

V1 does not include:
- automatic email sending
- automatic job applications
- investment account access
- computer control
- voice
- iMessage access
- full Gmail reading
- full Google Drive reading
- multi-user support
- mobile app
- web dashboard

## 4. User Domains

The first version should track these domains:

1. Academics
2. 2027 Summer Internship
3. Skills I Want to Learn
4. Health / Soccer
5. Life Admin

Future domains:
6. Finance / Investing
7. Relationships / Reflection

## 5. Data Model

### goals

A goal is a long-term or medium-term objective.

Fields:
- id
- domain
- title
- description
- why_it_matters
- target_date
- status
- weekly_target
- success_metric
- created_at
- updated_at

### tasks

A task is a concrete action.

Fields:
- id
- domain
- title
- description
- due_date
- priority
- status
- estimated_minutes
- source
- related_goal_id
- created_at
- updated_at

### daily_checkins

A daily check-in records what happened today.

Fields:
- id
- date
- planned_top_3
- completed
- blockers
- energy_level
- mood
- notes
- tomorrow_focus
- created_at

### agent_runs

An agent run records each proactive or reactive assistant action.

Fields:
- id
- run_type
- input_summary
- output
- created_at
- status
- error_message

## 6. Morning Briefing Behavior

Every morning, the assistant should generate a briefing.

Inputs:
- active goals
- open tasks
- due or overdue tasks
- previous daily check-in
- current date

Output:
- short greeting
- fixed commitments if available
- urgent tasks
- top 3 priorities
- recommended time blocks
- one long-term goal action
- one risk warning
- concise motivational note

Tone:
- direct
- supportive
- not too long
- accountability-focused

## 7. Evening Check-in Behavior

Every evening, the assistant should ask the user to check in.

It should ask:
1. Did you finish today's top 3?
2. What did you complete today?
3. What got blocked?
4. How was your energy from 1 to 10?
5. What should be tomorrow's main focus?

When the user replies, the assistant should parse the reply and store it as a daily_checkins record.

## 8. Weekly Review Behavior

Every Sunday evening, the assistant should generate a weekly review.

Inputs:
- goals
- tasks completed this week
- tasks not completed this week
- daily check-ins from this week

Output:
- what went well
- where the user fell behind
- patterns
- next week's measurable targets
- suggested focus areas
- honest but supportive advice

## 9. Safety Rules

The assistant must never take irreversible external actions without explicit user approval.

Requires approval:
- sending emails
- sending messages to other people
- submitting applications
- making purchases
- deleting files
- changing calendar events
- making financial trades
- sharing private information

V1 should not implement any of these actions.

## 10. Recommended Tech Stack

Backend:
- Python
- FastAPI

Agent workflow:
- LangGraph

Database:
- Supabase Postgres

LLM:
- OpenAI API

Chat interface:
- Telegram Bot

Scheduler:
- APScheduler for local/dev
- later replace with Temporal or cloud scheduler if needed

Deployment:
- local first
- later Render/Fly.io/Railway

## 11. Initial API Endpoints

The backend should expose:

- GET /health
- POST /telegram/webhook
- POST /agent/morning-briefing
- POST /agent/evening-checkin
- POST /agent/weekly-review
- POST /tasks
- GET /tasks
- POST /goals
- GET /goals

## 12. Development Rule

Build this project step by step.

Do not build all features at once.

Implementation order:
1. create backend skeleton
2. connect database
3. create database tables
4. add goals/tasks APIs
5. add Telegram bot
6. add OpenAI generation for morning briefing
7. add scheduler
8. add evening check-in parser
9. add weekly review
10. add calendar integration later
