# JARVIS MANUAL TEST CHECKLIST v1

> Rule:
> - Mark [x] if PASS
> - Mark [ ] if FAIL
> - Note latency/crashes if any.

---

## NLP

- [x] `hello`
- [x] `youtube kholo`
- [ ] `open youtube and search interstellar trailer`
- [ ] `play believer on youtube`
- [x] `mera naam kya hai`
- [x] `what is my name`
- [ ] `who am i`
- [ ] `who created you`

---

## MEMORY

- [x] `remember my name is Abhinav`
- [ ] Restart JARVIS and ask `what is my name`
- [x] `remember my dream is to build AGI`
- [x] `what is my dream`
- [x] `remember that I like anime`
- [ ] `what are my interests`
- [x] `what did I ask 2 prompts ago`

---

## TOOL CALLING

- [x] Open YouTube.
- [x] Open GitHub.
- [x] Open VS Code.
- [x] Open Notepad.
- [ ] Open Camera.
- [x] Open Calculator.

---

## VISION

- [x] Take Screenshot.
- [ ] Analyze Screenshot.
- [ ] `what's on my screen`
- [x] `what windows are open`
- [x] `which app is active`

---

## SPEECH

- [x] Speech mode starts.
- [x (but listening is horribly bad)] Microphone input works.
- [ ] ElevenLabs speaks response.
- [x] Text + Speech both work.

---

## CONTEXT

- [x] `take screenshot`
- [ ] `analyze it`
- [x] `open youtube`
- [ ] `search there for black holes`
- [x] `remember my dream`
- [x] `what is it`

---

## OLLAMA FALLBACK

- [x] Disable API keys.
- [x] Verify Ollama loads automatically.
- [x] Conversation continues without interruption.

---

## STABILITY

- [x] No crashes in 20 commands.
- [x] Average latency < 1 second.
- [x] Memory survives restart.
- [ ] No hallucinated memories.
- [x] No fake success messages.

---

## FINAL RESULT

| Category | Status |
|---------|--------|
| NLP | / FAIL |
| Memory |  / FAIL |
| Tool Calling | / FAIL |
| Vision | / FAIL |
| Speech | PASS  |
| Context | PASS  |
| Ollama | PASS  |
| Stability | PASS  |

---
