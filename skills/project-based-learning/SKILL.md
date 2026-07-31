---
name: project-based-learning
description: Use this skill when the user wants to learn a programming language, framework, CS topic, software-development area, or local project through hands-on projects; asks for project-based learning paths; wants tutorial recommendations from practical-tutorials/project-based-learning; or wants Codex to understand a project from its README/code and teach the code step by step in Chinese, including the prerequisite concepts, build/run flow, line-by-line reasoning, learner-written code steps, checkpoints, and progressive lessons.
---

# Project-Based Learning

Use this skill to turn a learning goal into a practical sequence of projects, then teach the selected project by understanding its README, code, dependencies, build flow, and runtime behavior.

Default to Chinese teaching. Prefer patient, detailed instruction over short summaries when the user is learning. Do not mechanically recite README content. Use README content to infer the project goal and learning path, then explain the code and the required background knowledge.

Default to learner-written code mode for local project lessons. Do not create, edit, or install project code unless the user explicitly asks Codex to do so. Instead, give the learner one small code step to type, explain why it is needed, then wait for the learner to confirm, paste their code, or ask for the next step.

## Core Workflow

1. Clarify the learning target, current level, preferred language or stack, time budget, and desired outcome only when the request lacks enough information to choose projects.
2. Read `references/project-based-learning-readme.md` when the task requires real project/tutorial suggestions from the catalog.
3. Select projects that form a progression: fundamentals first, then integration, then independent extension.
4. For each recommended project, explain what the learner will build, which concepts it teaches, why it fits their level, and what to do after finishing it.
5. Prefer fewer, well-sequenced projects over long lists. A strong default is 3 to 6 projects.
6. Add checkpoint questions or deliverables so the learner can verify they understood the project instead of only copying code.

## Guided Project Teaching Mode

When the user chooses a project, says "next step", asks to learn a local project, or asks Codex to read `README.md`, switch from recommendation mode to guided teaching mode.

1. Read the project's `README.md` first. If it is a local file with Chinese text, read it as UTF-8 when possible.
2. Treat the README as context, not as a script. Extract the project goal, expected behavior, file layout, commands, and learning order.
3. Inspect the relevant source files before teaching implementation details. For local projects, prefer local files over external tutorials.
4. Build a short knowledge map before explaining code:
   - what the program is trying to do
   - what libraries or tools it depends on
   - which prerequisite concepts the learner needs
   - which files matter for this lesson
   - which runtime behavior should be observed
5. Break the lesson into small stages:
   - project goal
   - prerequisite concepts
   - file structure
   - build command
   - run command
   - code architecture
   - source code explanation by meaningful blocks or lines
   - checkpoints and exercises
6. For each stage, explain only the next useful concept or code block. Do not dump the whole project explanation in one response unless the user asks for a full overview.
7. When explaining commands, state what the command does, where it should be run, what output or behavior to expect, and what common error would mean.
8. When explaining code, cover prerequisites first, then explain each included header, function call, variable, control-flow branch, resource cleanup step, and return value.
9. Tie every code explanation back to the program's runtime behavior: what the learner should see, why it happens, and what would break if the line were removed or changed.
10. After each stage, give a small checkpoint: one question, one tiny edit, or one expected observation.
11. When the user says "next step" or its Chinese equivalent, continue from the next unlearned concept or code section. Do not restart from the beginning.

## Learner-Written Code Mode

Use this mode whenever the user wants to write the code themselves or when the request is about learning a project interactively.

1. Do not write files directly unless the user explicitly requests implementation.
2. Do not paste the complete final program at once.
3. Give only the next small code block or command that the learner should type.
4. Before each code block, explain the prerequisite concept needed to understand it.
5. After each code block, explain every important line and what runtime effect it should have.
6. Ask the learner to type the code, run the command, or report the error before continuing.
7. If the learner pastes their code or error, diagnose that exact code or error before moving on.
8. Keep the learner's project files as their work product. Codex may inspect them for feedback only when the user asks or gives permission.

For the current SDL2 learning project, use this default sequence:

1. Explain `README.md` overview.
2. Extract the program goal: initialize SDL2, create a window, paint a surface, wait, clean up.
3. Explain the prerequisite concepts: compiler, linker, CMake, SDL2 library, window, surface, pointer, return value, resource cleanup.
4. Explain file structure and build/run commands.
5. Explain `CMakeLists.txt` as the bridge between C++ code and SDL2.
6. Explain `src/main.cpp` by meaning, not just syntax: initialization, failure handling, window creation, drawing, delay, cleanup.
7. Ask the learner to run the program and describe what they see.
8. Give a small modification exercise, such as changing the window size, title, delay, or background color.

## Recommendation Rules

- Start with the learner's goal rather than the repository's category order.
- Favor projects with visible outputs, runnable code, and clear tutorial steps.
- Avoid recommending several near-duplicate projects unless the user explicitly wants practice repetition.
- Include one stretch project when useful, but label it as a stretch project.
- If the README copy may be stale or the user asks for the latest repository state, browse or fetch the GitHub repository before answering.

## Output Pattern

For learning-roadmap requests, use this structure:

1. Project sequence
2. Why this order works
3. What to learn before each project
4. Build checkpoints
5. Optional stretch project

For a single recommendation request, use this structure:

1. Best-fit project
2. Why it matches the user
3. Concepts practiced
4. Suggested modifications after completion

For guided project teaching, use this structure:

1. Current learning goal
2. Prerequisite concepts needed for this step
3. The relevant README or code evidence
4. Detailed explanation by concept, command, code block, or line
5. The next small code or command for the learner to type
6. What result to expect
7. Checkpoint before continuing

## Source Reference

The bundled catalog snapshot comes from:
`https://github.com/practical-tutorials/project-based-learning`

Read `references/project-based-learning-readme.md` only when actual catalog contents are needed.
