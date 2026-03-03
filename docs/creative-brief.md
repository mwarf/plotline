# Creative Brief Guide

A creative brief guides Plotline's AI analysis to align the narrative with your project goals. It defines key messages, target audience, tone, and constraints that shape theme extraction, synthesis, and narrative arc construction.

---

## Quick Start

```bash
# Attach a brief to your project
plotline brief brief.md

# Or use YAML format
plotline brief brief.yaml --show
```

The brief is parsed and saved to `brief.json` in your project directory. It then influences all subsequent LLM analysis passes.

### Minimal Brief

```markdown
# Key Messages

- Libraries build community
- Access to information is a human right
```

That's the minimum required. Add more sections as needed.

---

## Format Specification

Plotline accepts briefs in **Markdown** or **YAML** format. Both are parsed into the same internal structure.

### Markdown Format

Create a `.md` file with standard headings. Headings are case-insensitive and support flexible naming.

```markdown
# Key Messages

- First message
- Second message
- Third message

# Audience

Description of your target audience.

# Target Duration

3-5 minutes

# Tone

Professional but warm, approachable.

# Must Include

- Customer testimonials
- Product demonstration

# Avoid

- Technical jargon
- Competitor comparisons
```

#### Supported Headings

| Heading | Field Name | Required | Notes |
|---------|------------|----------|-------|
| `# Key Messages` | `key_messages` | **Yes** | List of core messages |
| `# Audience` | `audience` | No | Target viewer description |
| `# Target Duration` or `# Length` | `target_duration` | No | Desired video length |
| `# Tone` or `# Tone Direction` | `tone_direction` | No | Stylistic guidance |
| `# Must Include` or `# Must Cover` | `must_include_topics` | No | Required topics/elements |
| `# Avoid` | `avoid_topics` | No | Topics to exclude |

#### Markdown Parsing Rules

- **Key Messages**: Parsed as a bulleted list (`-` or `*`). If no bullets found, the entire paragraph becomes a single message.
- **Other sections**: Bulleted lists or plain paragraphs both work.
- **Heading levels**: H1 (`#`), H2 (`##`), or H3 (`###`) are all recognized.

### YAML Format

Create a `.yaml` or `.yml` file with structured data:

```yaml
name: "Corporate Video Brief"
key_messages:
  - Innovation drives our success
  - Customer satisfaction is our priority
  - Our team makes the difference

audience: "Decision-makers in enterprise technology"
target_duration: "3-5 minutes"
tone_direction: "Professional, confident, inspiring"

must_include_topics:
  - Product demo footage
  - Customer testimonials
  - Team interviews

avoid_topics:
  - Technical jargon
  - Competitor comparisons
```

#### YAML Key Names

Both snake_case and camelCase are supported:

| snake_case | camelCase |
|------------|-----------|
| `key_messages` | `keyMessages` |
| `target_duration` | `targetDuration` |
| `tone_direction` | `toneDirection` |
| `must_include_topics` | `mustIncludeTopics` |
| `avoid_topics` | `avoidTopics` |

#### Advanced: Custom Message IDs

For precise tracking, define messages as objects with custom IDs:

```yaml
key_messages:
  - id: "msg_innovation"
    text: "Innovation drives our success"
  - id: "msg_customer"
    text: "Customer satisfaction is our priority"
  - id: "msg_team"
    text: "Our team makes the difference"
```

Custom IDs appear in the coverage matrix and synthesis output, making it easier to track which segments deliver which messages.

#### Extra Fields

YAML briefs preserve additional fields for your reference:

```yaml
name: "Q4 Campaign Brief"
title: "Product Launch Video"
summary: "A 3-minute brand video for the Q4 product launch."
project: "Project Alpha"

key_messages:
  - First message
```

Extra fields (`name`, `title`, `summary`, `project`) are stored in `brief.json` and displayed in reports.

---

## Section Details

### Key Messages (Required)

The core statements your video must communicate. Each message should be:
- **Concise**: One sentence, clear and memorable
- **Distinct**: Not overlapping with other messages
- **Verifiable**: You can identify when a segment delivers it

**Good:**
```markdown
# Key Messages

- Our software reduces operational costs by 40%
- Customers see ROI within 90 days
- 24/7 support ensures business continuity
```

**Avoid:**
```markdown
# Key Messages

- We're great (too vague)
- Our product is innovative and cutting-edge and revolutionary (too long)
- See above (not self-contained)
```

**Recommended count**: 3-7 messages. Fewer = clearer focus; more = diluted coverage tracking.

### Audience

Who will watch this video? Be specific about:
- Role/title
- Industry or context
- Knowledge level
- What they care about

```markdown
# Audience

CFOs and finance directors at mid-market SaaS companies (100-500 employees). 
They care about ROI, cost reduction, and operational efficiency. 
They're skeptical of marketing claims and want concrete numbers.
```

This helps the AI select segments with appropriate jargon, examples, and persuasion style.

### Target Duration

The desired length of your final video.

```markdown
# Target Duration

3-5 minutes
```

Or more specific:

```yaml
target_duration: "180 seconds"
```

The AI uses this to:
- Select an appropriate number of segments
- Balance pacing across the narrative arc
- Flag if selected segments exceed or fall short

### Tone Direction

The emotional and stylistic character of the video.

```markdown
# Tone

Professional but warm. Confident without being arrogant. 
Inspiring but grounded in reality. Avoid hyperbole.
```

The AI considers tone when:
- Selecting between segment candidates
- Determining narrative pacing
- Writing editorial notes in the arc

### Must Include

Topics, elements, or content that must appear in the final video.

```markdown
# Must Include

- Customer testimonial from Acme Corp
- Product demo showing the dashboard
- Mention of the free trial offer
- Closing call-to-action
```

The coverage report highlights which must-include items are covered and which are gaps.

### Avoid

Topics, words, or themes to exclude from the final video.

```markdown
# Avoid

- Competitor names (especially TechCorp and DataFlow)
- Pricing specifics
- Roadmap/unreleased features
- The word "revolutionary"
```

Segments touching on avoid topics are flagged during theme extraction for brand profiles.

---

## Profile-Specific Usage

### Documentary Profile

For documentary projects, the brief is **optional** and guides the AI more gently:

```markdown
# Key Messages

- Libraries serve as community anchors
- Digital access has transformed library services
- Libraries provide sanctuary and belonging

# Tone

Reverent, contemplative. Let subjects tell their own stories.
Avoid didactic narration or heavy-handed messaging.
```

Documentary briefs focus on:
- Thematic direction rather than strict message delivery
- Tone and pacing guidance
- Avoiding clichés or overused angles

### Brand Profile

For brand/corporate videos, the brief is **highly recommended** and drives strict message alignment:

```markdown
# Key Messages

- Our platform reduces time-to-market by 50%
- Enterprise-grade security is built into everything we do
- Customer success is our success

# Audience

VPs of Engineering and CTOs at Fortune 500 companies.
Technical background, skeptical of marketing fluff.

# Tone

Confident, technical, trustworthy. Lead with evidence, not adjectives.

# Must Include

- Customer logo montage
- Security certifications mention
- Free trial call-to-action

# Avoid

- Competitor names
- Unsubstantiated claims
- "AI-powered" (overused)
```

Brand briefs enable:
- Message-to-segment alignment tracking
- Coverage gap identification
- Off-message segment flagging

### Commercial Documentary Profile

A hybrid approach for branded documentaries:

```markdown
# Key Messages

- Authentic storytelling builds brand trust
- Our customers' success defines our success
- We invest in communities, not just products

# Tone

Journalistic, human-centered. Not promotional.
Let real people tell real stories.

# Must Include

- At least 3 customer voices
- Community impact example
- Subtle brand presence (logo, mention)

# Avoid

- Sales language
- Scripted testimonials
- Overproduction
```

---

## How the Brief Affects Pipeline Stages

| Stage | Command | Brief Usage |
|-------|---------|-------------|
| **Themes** | `plotline themes` | Brand profile maps segments to key messages; flags off-message content |
| **Synthesize** | `plotline synthesize` | Identifies "best takes" for each key message across all interviews |
| **Arc** | `plotline arc` | Ensures message coverage; flags gaps in coverage_gaps output |
| **Flags** | `plotline flags` | Cultural sensitivity check (independent of brief) |
| **Coverage Report** | `plotline report coverage` | Visualizes message-to-theme alignment; highlights gaps |

### Example: Arc Stage with Brief

When building the narrative arc, the AI:
1. Reviews all key messages from the brief
2. Selects segments that deliver each message
3. Assigns `brief_message` field to segments
4. Populates `coverage_gaps` array with any missing messages

```json
{
  "arc": [
    {
      "segment_id": "interview_001_seg_042",
      "brief_message": "msg_001",
      "editorial_notes": "Strong delivery of innovation message..."
    }
  ],
  "coverage_gaps": [
    "msg_003 not directly addressed in selected segments"
  ]
}
```

---

## Validation Rules

### Required Fields

| Field | Requirement |
|-------|-------------|
| `key_messages` | **Required** — at least one message |

### Auto-Normalization

Key messages are automatically normalized to `{id, text}` objects:

**Input (string):**
```yaml
key_messages:
  - First message
  - Second message
```

**Normalized:**
```json
{
  "key_messages": [
    {"id": "msg_001", "text": "First message"},
    {"id": "msg_002", "text": "Second message"}
  ]
}
```

IDs are auto-generated as `msg_001`, `msg_002`, etc. unless you provide custom IDs in YAML.

### Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `FileNotFoundError` | Brief file doesn't exist | Check file path |
| `ValueError: at least one key message` | No key messages found | Add `# Key Messages` section |
| `YAMLError` | Invalid YAML syntax | Validate YAML syntax |

---

## Best Practices

### 1. Right-Size Your Brief

| Project Type | Key Messages | Other Sections |
|--------------|--------------|----------------|
| Short social cut | 1-2 | Tone only |
| Brand video (2-3 min) | 3-5 | All sections |
| Documentary (10+ min) | 3-7 | Tone, Must Include |
| Long-form series | 5-10 per episode | Full brief per episode |

### 2. Write Actionable Messages

**Weak:**
```markdown
- We're innovative
- Quality matters
- Customer focus
```

**Strong:**
```markdown
- Our R&D team ships 200+ improvements per quarter
- 99.9% uptime SLA with 24/7 monitoring
- Dedicated customer success manager for every account
```

### 3. Be Specific in Tone

**Vague:**
```markdown
# Tone

Professional.
```

**Specific:**
```markdown
# Tone

Confident but not arrogant. Technical but accessible.
Lead with evidence and numbers, not adjectives.
Avoid superlatives (best, leading, revolutionary).
```

### 4. Use "Avoid" Sparingly

Too many avoid topics constrain the AI unnecessarily. Focus on:
- Legal/compliance requirements
- Brand guideline violations
- True deal-breakers

### 5. Iterate Based on Coverage

After running `plotline arc`:
1. Open the coverage report: `plotline report coverage`
2. Identify gaps (messages with weak/no coverage)
3. Either adjust the brief or look for additional interview material
4. Re-run: `plotline arc --force`

---

## Troubleshooting

### "Brief must contain at least one key message"

The parser couldn't find a `# Key Messages` section.

**Fix:**
```markdown
# Key Messages

- Your first message here
```

### Brief Not Affecting Output

Make sure you ran the pipeline **after** attaching the brief:

```bash
# Attach brief
plotline brief brief.md

# Re-run pipeline stages that use brief
plotline themes --force
plotline synthesize --force
plotline arc --force

# Or run full pipeline
plotline run --force
```

### Coverage Report Shows "No Brief Attached"

The coverage report requires a brief to be attached.

**Fix:**
```bash
plotline brief brief.md
plotline report coverage
```

### Custom IDs Not Appearing

Custom IDs only work in YAML format:

```yaml
key_messages:
  - id: "custom_id_here"
    text: "Your message"
```

Markdown briefs always generate sequential IDs (`msg_001`, etc.).

### Encoding Issues

If your brief contains special characters, ensure UTF-8 encoding:

```bash
# Check encoding
file brief.md

# Convert if needed
iconv -f ISO-8859-1 -t UTF-8 brief.md > brief_utf8.md
```

---

## Command Reference

```bash
# Attach brief (Markdown)
plotline brief path/to/brief.md

# Attach brief (YAML)
plotline brief path/to/brief.yaml

# View parsed brief
plotline brief brief.md --show

# After attaching, re-run affected stages
plotline themes --force
plotline synthesize --force
plotline arc --force

# View coverage
plotline report coverage
```

---

## Example Briefs

### Brand Video (Full)

```markdown
# Key Messages

- Our platform reduces operational costs by 40% on average
- Customers see measurable ROI within 90 days
- Enterprise-grade security with SOC 2 Type II certification
- 24/7 dedicated support ensures business continuity

# Audience

VPs of Operations and CFOs at mid-market companies (100-1000 employees).
They're cost-conscious, risk-averse, and value proof over promises.
They've likely been burned by vendor over-promising before.

# Target Duration

3 minutes (± 15 seconds)

# Tone

Confident, evidence-based, trustworthy. Lead with numbers and customer proof.
Avoid marketing fluff, superlatives, and unsubstantiated claims.
Technical details are welcome—audience is sophisticated.

# Must Include

- At least one customer testimonial (preferably Acme Corp)
- Specific ROI number or percentage
- Security certification mention
- Clear call-to-action at the end

# Avoid

- Competitor names
- Pricing specifics (direct to sales)
- "AI-powered" or "revolutionary" (overused)
- Future product roadmap
```

### Documentary (Minimal)

```markdown
# Key Messages

- Public libraries serve as democratic institutions open to all
- Libraries adapt to serve evolving community needs
- Librarians are community builders, not just book keepers

# Tone

Observational, human-centered. Let subjects drive the narrative.
Avoid voice-of-god narration or didactic messaging.
```

### Branded Documentary (Balanced)

```yaml
name: "Community Impact Series"

key_messages:
  - id: "impact_msg"
    text: "Our stores create economic opportunity in underserved communities"
  - id: "people_msg"
    text: "Real people share real stories of growth and opportunity"
  - id: "values_msg"
    text: "Community investment reflects our core values"

audience: "General public, potential employees, community stakeholders"

target_duration: "5-7 minutes"

tone_direction: |
  Authentic, human, hopeful but not saccharine.
  Avoid feeling like a corporate CSR video.
  Let community members speak for themselves.
  Subtle brand presence—logo, uniform, mention—but not center stage.

must_include_topics:
  - At least 3 community member voices
  - Local economic data or job creation numbers
  - Visual evidence of community investment

avoid_topics:
  - Sales promotions or pricing
  - Corporate executives (keep it grassroots)
  - Overly produced feel
```

---

## Related Documentation

- [Workflow Guide](workflow-guide.md) — End-to-end Plotline workflow
- [README](../README.md) — Full CLI reference and installation
