# Demo Brain notes

These are fictional everyday notes for showing the Brain graph. They are examples, not facts about the person using Poseidon.

From the repository root, copy them into your local vault:

```powershell
venv\Scripts\python.exe backend/scripts/seed_demo_brain.py
```

Then select **Scan raw sources** in the Brain view, or call `POST /brain/sync` on the running local backend. The seeding command only creates missing files under `memory-store/brain/raw/demo/`; it does not overwrite existing notes. Poseidon keeps the local vault out of Git.

Questions to try after scanning:

- What should I buy for Saturday lunch?
- What is due before the project review?
- How does the meal plan fit the grocery budget?
- What home maintenance needs attention this month?
- What should I pack for the weekend trip?
