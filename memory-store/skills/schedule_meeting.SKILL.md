---
name: Schedule Meeting
description: How to schedule a meeting or event when the user asks
triggers: [schedule, meeting, book, appointment, calendar, event]
---

When the user asks to schedule a meeting or event:

1. **Extract the key details** from the user's message:
   - Who is the meeting with?
   - What date and time?
   - What is the purpose/topic?
   - What is the preferred duration? (default: 30 minutes)

2. **Check for conflicts** by looking at the user's calendar for that time slot.

3. **Confirm the details** with the user before creating the event:
   - "I'll schedule a [duration] meeting with [person] on [date] at [time] about [topic]. Shall I go ahead?"

4. **Create the event** using the `calendar` tool (create action).

5. **Confirm** that the event was created successfully, including the final time and any notes.

**Important:** If the user mentions a person by name, check semantic memory for any preferences
(e.g., "Alex prefers morning meetings") and suggest a time that respects those preferences.
