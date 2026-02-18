# PROMPTS.md — Writing LLM Prompt Templates

## How Prompts Work in Plotline

The LLM analysis layer (Phase 5) uses three sequential passes, each with its own prompt template. Templates are plain text files with Jinja2 variable substitution. They live in the project's `prompts/` directory and are fully editable by the user.

```
prompts/
├── themes.txt           # Pass 1: Single-interview theme extraction
├── themes_brand.txt     # Pass 1 variant: Theme extraction with brief alignment
├── synthesize.txt       # Pass 2: Cross-interview synthesis
├── arc.txt              # Pass 3: Narrative arc construction
└── flags.txt            # Optional: Cultural content flagging
```

## Template Variables

These variables are available in all templates:

| Variable | Type | Description |
|----------|------|-------------|
| `{{TRANSCRIPT}}` | string | Formatted enriched transcript (segments with delivery labels) |
| `{{THEME_MAP}}` | string | Theme extraction results (Pass 2+ only) |
| `{{SYNTHESIS}}` | string | Cross-interview synthesis (Pass 3 only) |
| `{{NARRATIVE_BRIEF}}` | string | Parsed creative brief content (if attached) |
| `{{TARGET_DURATION}}` | string | Target piece duration, e.g., "12 minutes" |
| `{{PROFILE}}` | string | Active profile name: "documentary", "brand", or "commercial-doc" |
| `{{INTERVIEW_COUNT}}` | int | Number of interviews in the project |
| `{{INTERVIEW_ID}}` | string | Current interview ID (Pass 1 only) |
| `{{SPEAKER_NAME}}` | string | Interviewee name if known (from config) |

## Transcript Formatting

When `{{TRANSCRIPT}}` is rendered, each segment is formatted as:

```
[SEG_001] 00:02:15 → 00:02:41 | Delivery: moderate energy, varied pitch, measured pace
"When I was young, my grandmother would take us to the river every morning before the sun came up."

[SEG_002] 00:02:44 → 00:03:18 | Delivery: quiet, deliberate, 2.8s pause before — reflective
"She taught us that the water carries memory. That it remembers everything we bring to it."

[SEG_003] 00:03:22 → 00:03:55 | Delivery: rising energy, speech rate increases — animated
"And we believed her! Every morning, rain or shine, we'd be down there at the bank."
```

This format gives the LLM:
- Segment IDs it can reference in its response
- Timecodes for context
- Delivery labels so it can factor in how things were said
- The actual text

## Output Format Requirements

**Every prompt must instruct the LLM to respond in valid JSON.** The parsing layer (`plotline/llm/parsing.py`) expects structured output matching the schemas in ARCHITECTURE.md.

Include these instructions at the end of every prompt:

```
RESPONSE FORMAT:
Respond with valid JSON only. No markdown, no backticks, no preamble, no explanation outside the JSON structure.

Your response must be a single JSON object matching this structure:
[paste the relevant schema excerpt]
```

Include a few-shot example in the prompt so the LLM has a concrete model to follow. This dramatically improves output reliability.

## Writing Effective Prompts

### General Principles

1. **Role-set first.** Open with who the LLM is: "You are an experienced documentary editor reviewing interview footage." This anchors the analysis in editorial thinking, not generic summarization.

2. **Delivery labels are your differentiator.** Explicitly instruct the LLM to factor delivery into its decisions. Without this instruction, most LLMs will ignore the delivery data and select purely on text content.

3. **Be specific about what "good" means.** Don't say "find the best segments." Say "find segments where emotional delivery is strongest — slow speech, long pauses, vocal shifts — combined with thematic significance."

4. **Constrain the output.** Specify how many themes to find, how many segments to select, what duration to target. Unconstrained prompts produce sprawling, unusable output.

5. **Ask for reasoning.** "For each selection, explain in 1-2 sentences why this segment was chosen over alternatives." The reasoning appears in the review report and helps the editor evaluate the LLM's judgment.

### Documentary vs. Brand Prompting

The profile system configures which prompt template is used, but the actual editorial intelligence lives in the template text.

**Documentary prompts should emphasize:**
- Emotional authenticity over polish
- Moments of vulnerability, reflection, silence
- Non-linear narrative possibilities (circular, seasonal, associative)
- Thematic resonance across speakers
- Delivery analysis: pauses, voice drops, speech rate changes
- Cultural significance (for Indigenous content)

**Brand prompts should emphasize:**
- Message clarity and conciseness
- Alignment with creative brief key messages
- Speaker confidence and energy
- Coverage of all brief requirements
- Audience-appropriate language and complexity
- Best-take identification across multiple speakers

## Default Prompt Templates

### themes.txt — Pass 1: Theme Extraction (Documentary)

```
You are an experienced documentary editor reviewing a single interview transcript. Your task is to identify the major themes, recurring ideas, and emotional threads in this interview.

INTERVIEW:
{{TRANSCRIPT}}

INSTRUCTIONS:
1. Identify 3-8 major themes in this interview. A theme is a recurring idea, subject, or emotional current — not just a topic mentioned once.
2. For each theme, list which segment IDs contain material relevant to that theme.
3. Note where themes intersect — segments where multiple themes converge. These intersection points are often the most powerful editorial moments.
4. Describe the emotional character of each theme (e.g., "reverent and grounding" or "grief mixed with gratitude").
5. Rate each theme's strength from 0.0 to 1.0 based on how prominently it features in the interview.
6. Pay attention to the delivery labels. A segment delivered with emotional weight (slow speech, long pauses, voice changes) may be thematically significant even if the text seems simple.

RESPONSE FORMAT:
Respond with valid JSON only. No markdown, no backticks, no preamble.

{
  "themes": [
    {
      "theme_id": "theme_001",
      "name": "Short theme name",
      "description": "1-2 sentence description of this theme",
      "segment_ids": ["interview_001_seg_001", "interview_001_seg_005"],
      "emotional_character": "brief emotional descriptor",
      "strength": 0.85
    }
  ],
  "intersections": [
    {
      "segment_id": "interview_001_seg_014",
      "themes": ["theme_001", "theme_003"],
      "note": "Why these themes converge here"
    }
  ]
}
```

### themes_brand.txt — Pass 1: Theme Extraction (Brand)

```
You are a brand content strategist reviewing interview footage for a corporate video. Your task is to identify themes and map them to the creative brief's key messages.

CREATIVE BRIEF:
{{NARRATIVE_BRIEF}}

INTERVIEW:
{{TRANSCRIPT}}

INSTRUCTIONS:
1. Identify 3-6 themes in this interview, focusing on how they relate to the brand's key messages.
2. For each theme, note which key message(s) from the brief it supports.
3. Identify the single strongest segment for each key message — the moment where the speaker most clearly, confidently, and concisely delivers that message.
4. Pay attention to delivery: high energy, confident tone, and clear articulation score higher for brand content. Hesitation, rambling, or low energy are editorial concerns even if the content is on-message.
5. Flag any segments that are off-message or touch on topics in the "avoid" list.

RESPONSE FORMAT:
Respond with valid JSON only. No markdown, no backticks, no preamble.

{
  "themes": [
    {
      "theme_id": "theme_001",
      "name": "Short theme name",
      "description": "1-2 sentence description",
      "segment_ids": ["interview_001_seg_003", "interview_001_seg_012"],
      "emotional_character": "confident, forward-looking",
      "strength": 0.8,
      "brief_alignment": "msg_001"
    }
  ],
  "intersections": [...],
  "off_message_segments": [
    {
      "segment_id": "interview_001_seg_022",
      "reason": "Mentions competitor by name — in avoid list"
    }
  ]
}
```

### synthesize.txt — Pass 2: Cross-Interview Synthesis

```
You are a documentary editor reviewing theme maps from {{INTERVIEW_COUNT}} interviews. Your task is to find the connections — shared themes, complementary perspectives, contradictions, and convergence points across all interviews.

THEME MAPS:
{{THEME_MAP}}

INSTRUCTIONS:
1. Group related themes across interviews into unified themes. Three speakers talking about "connection to place" in different ways should become one unified theme.
2. For each unified theme, describe how the different speakers relate to it: complementary (different angles on the same idea), contradictory (opposing views), or expanding (each adds a new dimension).
3. Identify the 2-3 strongest segments for each unified theme — the moments with the best combination of content and delivery.
4. If a creative brief is present, map unified themes to key messages and identify which speaker delivers each message most effectively.
5. Note any themes that appear in only one interview — they may be unique and valuable, or they may be tangential.

{% if NARRATIVE_BRIEF %}
CREATIVE BRIEF:
{{NARRATIVE_BRIEF}}
{% endif %}

RESPONSE FORMAT:
Respond with valid JSON only. No markdown, no backticks, no preamble.

{
  "unified_themes": [
    {
      "unified_theme_id": "utheme_001",
      "name": "Theme name",
      "description": "How this theme manifests across interviews",
      "source_themes": [
        { "interview_id": "interview_001", "theme_id": "theme_001" },
        { "interview_id": "interview_003", "theme_id": "theme_002" }
      ],
      "all_segment_ids": ["interview_001_seg_001", "interview_003_seg_012"],
      "perspectives": "Description of how speakers relate to this theme",
      "brief_alignment": null
    }
  ],
  "best_takes": [
    {
      "topic": "Theme or message name",
      "candidates": [
        {
          "segment_id": "interview_001_seg_014",
          "interview_id": "interview_001",
          "rank": 1,
          "reasoning": "Why this is the strongest version"
        }
      ]
    }
  ]
}
```

### arc.txt — Pass 3: Narrative Arc Construction

```
You are an experienced documentary editor building a narrative arc from interview material. You have {{INTERVIEW_COUNT}} interviews with themes already identified and synthesized.

Your task: select and order segments into a {{TARGET_DURATION}} piece with a coherent narrative structure.

UNIFIED THEMES:
{{SYNTHESIS}}

ALL AVAILABLE SEGMENTS (enriched with delivery data):
{{TRANSCRIPT}}

{% if NARRATIVE_BRIEF %}
CREATIVE BRIEF:
{{NARRATIVE_BRIEF}}
{% endif %}

PROFILE: {{PROFILE}}

INSTRUCTIONS:
1. Select segments that form a coherent narrative arc. Not every good segment belongs — choose the ones that build on each other.
2. Assign each segment a role: opening, deepening, turning_point, climax, resolution, coda, or bridge.
3. Prioritize segments where strong delivery aligns with thematic significance. A quiet, deliberate moment about loss is more powerful than an energetic moment about the same topic if the delivery matches the content.
4. Consider pacing: alternate between high-energy and reflective moments. Don't cluster all the heavy material together.
5. The total duration of selected segments should approximate {{TARGET_DURATION}}. Each segment's duration can be calculated from its start/end times.
6. For each segment, provide editorial notes (why you chose it) and pacing suggestions (how to handle the edit points).
7. If the profile is "documentary," the arc can be non-linear, circular, or seasonal — follow the material, not a formula.
8. If the profile is "brand," ensure every key message from the brief is covered. Flag any coverage gaps.

RESPONSE FORMAT:
Respond with valid JSON only. No markdown, no backticks, no preamble.

{
  "target_duration_seconds": 720,
  "estimated_duration_seconds": 695,
  "narrative_mode": "emergent",
  "arc": [
    {
      "position": 1,
      "segment_id": "interview_001_seg_001",
      "interview_id": "interview_001",
      "role": "opening",
      "themes": ["utheme_001"],
      "editorial_notes": "Why this segment was chosen and what it does for the story",
      "pacing": "Specific editorial guidance for edit points",
      "brief_message": null
    }
  ],
  "coverage_gaps": [],
  "alternate_candidates": [
    {
      "for_position": 3,
      "segment_id": "interview_002_seg_018",
      "reasoning": "Strong alternative if the editor wants a different voice here"
    }
  ]
}
```

### flags.txt — Cultural Content Flagging

```
You are a cultural sensitivity reviewer. Review the following selected interview segments and flag any that may touch on culturally sensitive content requiring community review before publication.

SELECTED SEGMENTS:
{{TRANSCRIPT}}

Flag segments that reference:
- Ceremonial or sacred practices
- Sacred places or restricted sites
- Spiritual teachings not intended for public sharing
- Protocols around naming, death, or mourning
- Knowledge traditionally shared only in specific contexts (age, gender, season)
- Personal stories that may require consent beyond the original interview consent

For each flagged segment, explain specifically what triggered the flag and what kind of review may be needed.

This is an advisory system — it does not replace cultural consultation with appropriate knowledge holders.

RESPONSE FORMAT:
Respond with valid JSON only.

{
  "flags": [
    {
      "segment_id": "interview_001_seg_033",
      "reason": "References a specific ceremony by name — may require cultural review before publication",
      "review_type": "cultural_advisor",
      "severity": "review_recommended"
    }
  ]
}
```

## Testing Prompts

When modifying prompt templates, test them with this workflow:

1. **Prepare a sample input.** Use a real enriched segments.json from a test interview.
2. **Render the template.** `plotline themes --dry-run` should show the rendered prompt without sending it.
3. **Send to your LLM.** Test with both the local model (Ollama) and a cloud model (Claude) to compare quality.
4. **Validate the output.** Does it parse as valid JSON? Does it match the schema in ARCHITECTURE.md?
5. **Evaluate editorial quality.** Do the theme identifications make sense? Are the selections defensible? Would an editor trust these recommendations?

## Common Prompt Failure Modes

| Problem | Symptom | Fix |
|---------|---------|-----|
| LLM returns markdown instead of JSON | Parsing fails | Add "No markdown, no backticks" to format instructions. Add `\n\nJSON:` at the very end of the prompt. |
| LLM invents segment IDs | References nonexistent segments | Add a list of valid segment IDs to the prompt. Add "Only reference segments from the list provided." |
| LLM ignores delivery data | Selections based purely on text content | Make delivery labels more prominent in the transcript format. Add explicit instruction: "A segment with high delivery score and moderate content is preferable to one with high content and flat delivery." |
| Output too long / too many selections | Exceeds target duration | Add explicit constraint: "Select no more than N segments. Total duration must not exceed X seconds." |
| All selections from one interview | Other interviews ignored | Add: "Include material from at least N different interviews." |
| JSON has trailing commas or syntax errors | Parse error | Add a concrete JSON example in the prompt. Some models need to see the exact format. |
| Themes are too generic | "Community," "Family," "Culture" — not useful | Add: "Be specific. 'Connection to the river as a site of intergenerational teaching' is a theme. 'Nature' is not." |

## Context Window Considerations

| Model | Context Window | Can Handle |
|-------|---------------|------------|
| Llama 3.1 8B | 128K tokens | Single 90-min interview easily |
| Llama 3.1 70B | 128K tokens | Single 90-min interview easily |
| Claude Sonnet | 200K tokens | Multiple interviews in one pass |
| Claude Opus | 200K tokens | Full project synthesis |

A 60-minute interview produces roughly 8,000-12,000 words of transcript (~10K-15K tokens). With delivery metadata, expect ~15K-20K tokens per interview.

For Pass 2 (synthesis), you're sending theme maps, not full transcripts — typically under 5K tokens total.

For Pass 3 (arc), you may need to send full enriched segments for all interviews. For a 6-interview project, this could be 90K-120K tokens. If the model can't handle it, send only the top 50% of segments by composite score as candidates.
