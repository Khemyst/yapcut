We're building ClaudEdits — a tool that takes a timecoded transcript of a stream VOD and produces an FCP XML file that Premiere Pro can import as a rough cut sequence.
What this is NOT: An automated pipeline. There's no scoring engine, no computer vision, no rendering. This is a conversational editing workflow — I describe what I want from the edit, you read the transcript, we talk about it, and you output an XML file.
What this tool needs:

A CLAUDE.md that teaches future Claude Code instances how to work in this repo. It should cover:

What ClaudEdits is and how the workflow operates
The FCP XML schema (enough to generate valid Premiere-importable XML with video+audio tracks, clip items with in/out points referencing source media)
How to read the input transcript format (timecoded JSON — this comes from a separate tool's Stage 2 output, we'll define the schema based on what I provide)
Editorial guidelines and preferences (we'll build these out over time)
Media path conventions (source files live on my PC, we need a clean way to reference them)


A small Python utility that validates generated XML before I import it — checks well-formedness, verifies required FCP XML elements exist, flags any obvious structural problems.

Start by creating the project structure and drafting the CLAUDE.md. Don't overthink it — this is v0. We'll iterate.
My source media is on my PC at C:\Users\jaywa.NEUTRON\Videos\Streams\. Premiere Pro version is the latest Creative Cloud release.