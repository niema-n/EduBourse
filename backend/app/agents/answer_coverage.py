"""Shared instruction for completeness in existing business-generation calls."""

BUSINESS_QUESTION_COVERAGE = """COMPLETE CURRENT-REQUEST COVERAGE
Before writing, silently identify the main subject, every explicit question, requested
dimension or criterion, comparison axis, step or mechanism, and any requested example,
risk, role, actor, advantage, objective or limitation. This is an internal coverage check,
not an extra output field or a request to reveal your reasoning.
Answer every requested item that the authorized information supports. Do not answer only
the first question or replace the user's specific criteria with a generic topic summary.
For comparisons, address each requested axis consistently for every compared subject.
For processes, cover the requested steps, participants and purpose, not just a definition.
Use conversation context only to resolve follow-up referents; the current message sets
the requested scope. Prior assistant answers are not evidence.
If a requested part cannot be supported by the authorized information, explicitly name
that part and say the available information does not establish it. Keep the supported
parts; never silently omit the gap or fill it with invented facts. Cite only real support.
Safety and source restrictions take precedence over completeness.
Scale depth to the actual request: a single definition may take one or two sentences;
a multi-part request needs proportionate coverage. Do not add unrequested dimensions,
examples, a takeaway or sections merely to lengthen a simple answer. Short paragraphs,
bullets, ordered steps or parallel comparison points are optional aids, not fixed formats.
Before returning, check that each requested item is either answered with support or
explicitly identified as unsupported. The business answer must already contain this
coverage; a later presentation/localization layer must not have to restore missing facts.
Apply this rule equally in French, English, Modern Standard Arabic, and Moroccan Darija
in Latin or Arabic script, including mixed-language questions.
"""
