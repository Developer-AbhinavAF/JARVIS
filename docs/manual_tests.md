# Execution-first manual test matrix

Run these on the target Windows desktop with a controlled browser/app provider configured. Mark a case pass only after its stated verification occurs; an unavailable provider is a fail, not a pass.

| # | Request | Expected verified outcome |
|---:|---|---|
| 1 | hello | Concise greeting, no LLM request |
| 2 | thanks | Concise acknowledgement, no LLM request |
| 3 | yes | Concise acknowledgement, no LLM request |
| 4 | no | Concise acknowledgement, no LLM request |
| 5 | bye | Concise farewell, no LLM request |
| 6 | good morning | Concise greeting, no LLM request |
| 7 | good night | Concise farewell, no LLM request |
| 8 | open YouTube | Browser URL verified |
| 9 | open Chrome | Chrome process/window verified |
| 10 | open VS Code | VS Code process/window verified |
| 11 | open Camera | Camera process/window verified |
| 12 | play music | Media playback state verified |
| 13 | search Google for Ada Lovelace | Browser query verified |
| 14 | open Downloads | Folder/window verified |
| 15 | open README.md | File/window verified |
| 16 | take a screenshot | Output file verified |
| 17 | what time is it | Local clock result |
| 18 | weather in Delhi | Fresh provider result or verified failure |
| 19 | calculate 18 * 24 | Correct numeric result |
| 20 | what is my name | Natural semantic-memory response |
| 21 | who am I | Natural semantic-memory response |
| 22 | remember my name is Abhinav | Durable fact write verified |
| 23 | remember I prefer dark mode | Preference write verified |
| 24 | forget my name | Fact removal verified |
| 25 | summarize this paragraph | Level-2 bounded response |
| 26 | explain AI | Level-3 response |
| 27 | teach me Python lists | Level-3 response |
| 28 | explain relativity | Level-3 response |
| 29 | debug this traceback | Level-4 response |
| 30 | design a cache | Level-4 response |
| 31 | open YouTube then search jazz | Multi-step verified chain |
| 32 | open GitHub then search Ollama | Multi-step verified chain |
| 33 | open it | Previous entity resolved |
| 34 | search there for jazz | Current website resolved |
| 35 | do that again | Last command resolved |
| 36 | use the same app | Last entity resolved |
| 37 | open the previous file | Previous entity resolved |
| 38 | current app | Active application read verified |
| 39 | current window | Active window read verified |
| 40 | current folder | Current folder read verified |
| 41 | current tab | Browser tab state verified |
| 42 | current selection | Selection state read verified |
| 43 | current clipboard | Clipboard value read verified |
| 44 | analyze this screenshot | Screenshot context used |
| 45 | open a nonexistent app | Truthful verified failure |
| 46 | open a blocked URL | Truthful verified failure |
| 47 | screenshot without permission | Truthful verified failure |
| 48 | delete a missing file | Truthful verified failure |
| 49 | delete a real file | Explicit confirmation + removal verified |
| 50 | lock computer | Explicit confirmation + action verification |
| 51 | shut down computer | Explicit confirmation + action verification |
| 52 | sleep computer | Explicit confirmation + action verification |

Cases 53–100 repeat cases 1–48 in Hindi, Hinglish, alternate phrasings, and after a restart. In every variant verify: returned intent/confidence/entities/context, no Level-0/1/2 LLM reasoning, durable memory where relevant, and no unverified success message.
