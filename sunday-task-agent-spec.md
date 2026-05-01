# Sunday Task Agent — System Spec

## Overview

A Python agent that runs once per week (triggered by a scheduled task every Sunday afternoon), reaches out via Telegram to collect adult life tasks for the week, gathers details on each task one-by-one through conversation, and books them as events on Google Calendar. The program shuts down after all tasks have been scheduled.

---

## Architecture

### High-Level Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Cron/Systemd │────▶│ Python Agent  │────▶│ Telegram Bot  │────▶│   User (You) │
│  (Sunday 2PM) │     │  (main.py)   │◀────│  (Interface)  │◀────│              │
└──────────────┘     └──────┬───────┘     └──────────────┘     └──────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
               ┌────▼────┐    ┌────▼────┐
               │  Claude  │    │ Google  │
               │   API    │    │Calendar │
               │  (Brain) │    │  (Tool) │
               └─────────┘    └─────────┘
```

### Components

| Component         | Role                                                           | Technology                                       |
| ----------------- | -------------------------------------------------------------- | ------------------------------------------------ |
| **Scheduler**     | Triggers agent every Sunday                                    | `Task Scheduler` (Windows)                       |
| **Agent Core**    | Orchestrates the conversation loop, manages state, calls tools | Python, Gemini Free API                          |
| **Interface**     | Sends/receives messages with the user                          | Telegram Bot API (`python-telegram-bot`)         |
| **LLM**           | Parses tasks, drives conversation, decides when to call tools  | Free Google Gemini API (Google SDK)              |
| **Calendar Tool** | Creates event with date, time, duration, description           | Google Calendar API (`google-api-python-client`) |

### Why an Agent (Not a Workflow)

- **Non-deterministic task count**: The user might say 1 task or 7. A workflow would need to predefine branches or cap the number. An agent just loops until done.
- **Conversational follow-ups**: Each task may need different follow-up questions (a car task might need a shop location, a medical task might need a doctor's name). The LLM decides what to ask.
- **Tool extensibility**: Future tools (location search, price lookup, booking APIs) plug into the same agent loop without restructuring control flow.

---

## Agent Design

### Agent Loop (Core Logic)

```
┌─────────────────────────────────────────────────┐
│                  AGENT LOOP                      │
│                                                  │
│  1. Build messages array (system + history)       │
│  2. Call Google API with tools                    │
│  3. Process response:                             │
│     ├─ text → send to user via Telegram           │
│     ├─ tool_use → execute tool, append result     │
│     │            └─ loop back to step 1           │
│     └─ end_conversation tool → exit               │
│  4. Wait for user reply (via Telegram)            │
│  5. Append user message to history                │
│  6. Loop back to step 1                           │
└─────────────────────────────────────────────────┘
```

The agent is **not a state machine you manage** — the LLM _is_ the state machine. You provide it with the system prompt, tools, and conversation history. It decides what to do next: ask a question, call a tool, or end the conversation. Your code just executes what it asks for.

### System Prompt

The system prompt defines the agent's personality, goals, and behavioral rules. This is the most critical piece — it governs the entire conversation flow.

```
You are a weekly task planning assistant. Your job is to help the user
plan and schedule their adult responsibilities for the upcoming week.

## Conversation Flow

1. OPEN: Send the initial greeting asking for this week's tasks.
   Use a message like: "What are the must-do adult tasks this week?
   (Car, finances, medical, personal, chores)"

2. PARSE: When the user responds with tasks, split them into
   individual tasks. Confirm the list back to the user.
   Example: User says "change my brakes and wash my car"
   → Task 1: Change brakes
   → Task 2: Wash car
   Confirm: "I've got 2 tasks: (1) Change brakes, (2) Wash car.
   Let's get these scheduled. Starting with #1..."

3. DETAIL LOOP: For each task, one at a time:
   a. Ask what day this week they want to do it
   b. Ask what time
   c. Ask for estimated duration (suggest a default if obvious)
   d. Ask if there are any additional details (location, notes, etc.)
   e. Ask if he wants to be reminded and when
   f. Once you have enough info, call the `create_calendar_event` tool
   g. Confirm it's booked, then move to the next task

4. CLOSE: After all tasks are booked, summarize the week's schedule
   and call the `end_conversation` tool.

## Rules
- Always process tasks ONE AT A TIME. Never batch questions.
- If the user gives vague timing ("sometime Tuesday"), ask for
  a specific time or suggest a reasonable default.
- If the user says "nothing this week" or "none", acknowledge
  it and call end_conversation.
- If the user wants to add more tasks after initial intake,
  accept them and continue the loop.
- Keep messages concise. This is a Telegram chat, not an email.
- Use the current week's dates (Monday through Sunday) when
  interpreting days. "Tuesday" means the upcoming Tuesday.
```

### Tool Definitions

Tools are passed to the Claude API on every call. The agent decides when to use them.

#### Tool 1: `create_calendar_event`

```json
{
  "name": "create_calendar_event",
  "description": "Create an event on the user's Google Calendar. Call this once you have gathered sufficient details about a task (at minimum: title, date, and start time).",
  "input_schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Short, clear event title. e.g., 'Change brakes', 'Pay rent'"
      },
      "date": {
        "type": "string",
        "description": "Date in YYYY-MM-DD format. Must be within the current week."
      },
      "start_time": {
        "type": "string",
        "description": "Start time in HH:MM (24hr) format. e.g., '14:00'"
      },
      "duration_minutes": {
        "type": "integer",
        "description": "Duration in minutes. Default to 60 if not specified.",
        "default": 60
      },
      "description": {
        "type": "string",
        "description": "Optional notes or details about the task."
      },
      "location": {
        "type": "string",
        "description": "Optional location for the task."
      }
    },
    "required": ["title", "date", "start_time"]
  }
}
```

#### Tool 2: `end_conversation`

```json
{
  "name": "end_conversation",
  "description": "Call this when all tasks have been scheduled and the conversation is complete. This will shut down the agent.",
  "input_schema": {
    "type": "object",
    "properties": {
      "summary": {
        "type": "string",
        "description": "A brief summary of all tasks scheduled this session."
      }
    },
    "required": ["summary"]
  }
}
```

#### DO NOT INCLUDE. THESE ARE POTENTIAL FUTURE TOOLS (Extensibility)

These are not built in v1 but the agent architecture supports adding them without structural changes:

| Tool               | Purpose                                 | Example Use                                 |
| ------------------ | --------------------------------------- | ------------------------------------------- |
| `search_location`  | Find business addresses, hours, ratings | "Where should I get my brakes done?"        |
| `check_calendar`   | Read existing events to avoid conflicts | "You already have something at 3pm Tuesday" |
| `set_reminder`     | Push a notification before the event    | "Remind me 1 hour before"                   |
| `book_appointment` | Integrate with booking APIs             | "Book the 2pm slot at the mechanic"         |

---

## Conversation UX

### Example Conversation

```
AGENT: What are the must-do adult tasks this week?
       (Car, finances, medical, personal, chores)

USER:  Change my brakes and wash my car

AGENT: Got it — 2 tasks:
       1. Change brakes
       2. Wash car
       Let's schedule them. Starting with #1: Change brakes.
       What day do you want to do this?

USER:  Wednesday

AGENT: What time on Wednesday?

USER:  Morning, like 9

AGENT: 9:00 AM Wednesday. How long do you think it'll take?
       Brake changes usually run about 2 hours.

USER:  Yeah 2 hours sounds right
AGENT: When do you want to be reminded about this or no? if yes when [15 mins before, an hour, a day before or a custom]
USER: a day before
AGENT: [calls create_calendar_event]
       ✅ "Change brakes" booked for Wednesday 9:00 AM – 11:00 AM.
       Next up — #2: Wash car. What day?

USER:  Same day, afternoon

AGENT: What time in the afternoon?

USER:  3

AGENT: 3:00 PM Wednesday. Car washes usually take about 30–45 min.
       Want me to put 45 minutes?

USER:  Sure

AGENT: [calls create_calendar_event]
       ✅ "Wash car" booked for Wednesday 3:00 PM – 3:45 PM.
       That's everything! Here's your week:
       • Wed 9:00–11:00 AM — Change brakes
       • Wed 3:00–3:45 PM — Wash car
      Anything else?
USER: No not really

AGENT:
Ok Have a good week. 💪
[calls end_conversation]
```

### Edge Cases

| Scenario                             | Agent Behavior                                                                  |
| ------------------------------------ | ------------------------------------------------------------------------------- |
| **"Nothing this week"**              | Acknowledge, call `end_conversation`                                            |
| **Single task**                      | Skip the numbered list, go straight to details                                  |
| **User adds tasks mid-conversation** | Accept them, extend the task queue                                              |
| **Vague time ("sometime Tuesday")**  | Ask for a specific time or offer a suggestion                                   |
| **User corrects a task**             | Re-ask for that task's details, update if already booked                        |
| **User goes off-topic**              | Gently redirect: "Got it — anything else task-wise for this week?"              |
| **User is unresponsive (timeout)**   | After 30 min of no reply, send a nudge. After 2 hours, save state and shut down |
| **Telegram connection drops**        | Retry logic with exponential backoff, persist conversation history              |

---

## Technical Implementation

### Project Structure

```
sunday-task-agent/
├── main.py                 # Entry point — cron calls this
├── agent.py                # Agent loop logic
├── tools/
│   ├── __init__.py
│   ├── calendar_tool.py    # Google Calendar API wrapper
│   └── end_tool.py         # Shutdown handler
├── telegram_interface.py   # Telegram bot send/receive
├── config.py               # API keys, chat ID, calendar ID
├── requirements.txt
└── .env                    # Secrets (not committed)
```

### Key Implementation Details

#### Entry Point (`main.py`)

```python
# Pseudocode
def main():
    # 1. Initialize clients
    telegram = TelegramInterface(config.BOT_TOKEN, config.CHAT_ID)
    calendar = CalendarTool(config.GOOGLE_CREDENTIALS)
    claude = AnthropicClient(config.ANTHROPIC_API_KEY)

    # 2. Build initial messages
    messages = []  # Empty — system prompt handles the opener

    # 3. Run agent loop
    agent = Agent(claude, telegram, tools=[calendar])
    agent.run(messages)

    # 4. Agent loop exited (end_conversation was called)
    sys.exit(0)
```

#### Agent Loop (`agent.py`)

```python
# Pseudocode
class Agent:
    def run(self, messages):
        while True:
            # Call Claude
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=self.tool_definitions,
                max_tokens=1024
            )

            # Process response content blocks
            for block in response.content:
                if block.type == "text":
                    self.telegram.send(block.text)

                elif block.type == "tool_use":
                    if block.name == "end_conversation":
                        self.telegram.send(f"📋 {block.input['summary']}")
                        return  # Exit the loop → program shuts down

                    # Execute the tool
                    result = self.execute_tool(block.name, block.input)

                    # Append assistant response + tool result to history
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        }]
                    })
                    continue  # Back to top — let Claude react to tool result

            # If we sent text (not a tool call), wait for user reply
            if response.stop_reason == "end_turn":
                user_reply = self.telegram.wait_for_reply(timeout=7200)
                if user_reply is None:
                    self.telegram.send("No worries — we can pick this up next week.")
                    return
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": user_reply})
```

#### Telegram Interface

```python
# Key behaviors:
# - send(text): Push a message to the user's chat
# - wait_for_reply(timeout): Block until user responds or timeout
# - Uses long polling, NOT webhooks (no server needed)
#
# The bot must be created via @BotFather on Telegram.
# CHAT_ID is your personal Telegram user ID (get via @userinfobot).
```

#### Google Calendar Integration

```python
# Key behaviors:
# - Authenticate via service account or OAuth2 (stored credentials)
# - create_event(title, date, start_time, duration, description, location)
#   → Returns event ID and HTML link on success
#   → Returns error message on failure (e.g., auth expired)
#
# Uses: google-api-python-client, google-auth
# Calendar ID: your primary calendar or a dedicated "Tasks" calendar
```

### Scheduling (Cron)

```powershell
# Windows Task Scheduler (if running on Windows)
# Action: Start a program
# Program: python
# Arguments: C:\path\to\sunday-task-agent\main.py
# Trigger: Weekly, Sunday, 2:00 PM
```

### Dependencies

```

python-telegram-bot>=21.0
google-api-python-client>=2.100.0
google-auth>=2.25.0
google-auth-oauthlib>=1.2.0
python-dotenv>=1.0.0
```

### Environment Variables

```

TELEGRAM_BOT_TOKEN=123456:ABC-...
TELEGRAM_CHAT_ID=your_numeric_chat_id
GOOGLE_CALENDAR_ID=primary
GOOGLE_CREDENTIALS_PATH=./credentials.json
```

---

## Open Questions

1. **State persistence**: V1 will skip state persistence.

2. **Multi-day scheduling**: V1 will not include this.

3. **Task categories**: The prompt mentions categories (car, finances, medical, personal, chores). Should the agent tag events with categories/colors on Google Calendar?

4. **Recurring tasks**: "I wash my car every week" — should the agent remember this and pre-populate next week?

5. **Mid-week additions**: Should there be a way to trigger the agent outside Sunday? (e.g., text "add task" to the bot anytime)

6. **Confirmation before booking**: Should the agent confirm all details before calling `create_calendar_event`, or book immediately and let the user correct?
