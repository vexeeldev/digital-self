# Digital Self

> **A computational second version of the self that learns from lived experiences, forms associative memories, develops an internal state, and uses accumulated experience to reason about new situations.**

**Status:** Concept / Architecture Design  
**Version:** 0.1  
**Primary Goal:** Build a computational system that gradually develops a model of its owner through accumulated experiences rather than being manually programmed with a fixed personality.

---

# 1. Executive Summary

**Digital Self** adalah sebuah sistem yang mencoba membuat **versi digital kedua dari seseorang**.

Sistem ini bukan sekadar:

- chatbot pribadi,
- Second Brain,
- note-taking application,
- database kenangan,
- personality chatbot,
- atau AI assistant yang diberi prompt tentang kepribadian seseorang.

Digital Self dirancang sebagai **sistem memori dan reasoning yang berkembang dari pengalaman**.

Pengguna memasukkan pengalaman sehari-hari dalam bentuk natural language.

Contoh:

> "Tadi di kantor temanku sepatunya agak bau. Aku biasa aja. Terus waktu mau mengambil sesuatu aku kesandung dan lumayan kesal."

Sistem tidak langsung mengubahnya menjadi kesimpulan seperti:

> "User tidak suka sepatu bau."

Sebaliknya, pengalaman tersebut dipertahankan sebagai **raw experience**, kemudian dianalisis menjadi berbagai elemen:

```text
Experience
├── Context
│   └── Office
│
├── Person
│   └── Friend
│
├── Object
│   └── Shoes
│
├── Event
│   ├── Shoes smelled
│   └── User tripped
│
├── Emotional response
│   └── Annoyance
│
└── Reaction
    └── Neutral toward smell
```

Dari pengalaman tersebut sistem kemudian membentuk hubungan antar-elemen.

Pengalaman-pengalaman berikutnya dapat memperkuat, melemahkan, atau mengubah hubungan tersebut.

Dengan demikian, sistem tidak hanya menyimpan:

> **"Apa yang pernah terjadi?"**

tetapi secara bertahap mencoba membentuk:

> **"Apa yang sering terjadi?"**  
> **"Apa yang berkaitan dengan apa?"**  
> **"Bagaimana aku biasanya bereaksi?"**  
> **"Dalam kondisi apa aku berubah?"**  
> **"Apa yang pernah kulakukan ketika menghadapi situasi serupa?"**  
> **"Seberapa yakin sistem terhadap kesimpulan tersebut?"**

Tujuan akhirnya adalah membuat agent yang dapat menggunakan jaringan pengalaman tersebut ketika menghadapi situasi baru.

---

# 2. Problem Statement

AI assistant biasa memiliki pengetahuan umum yang sangat besar, tetapi tidak benar-benar memiliki sejarah hidup pengguna.

Sistem seperti chatbot personal biasanya menggunakan:

```text
User Profile
+
Preferences
+
Saved Memories
+
Conversation History
```

Model tersebut masih terlalu sederhana untuk merepresentasikan seseorang.

Manusia tidak menyimpan dirinya sebagai daftar:

```text
likes = ["technology"]
dislikes = ["noise"]
personality = ["curious"]
```

Pengalaman manusia jauh lebih kontekstual.

Contohnya:

```text
"Di kantor aku tidak terlalu terganggu suara berisik."

tidak sama dengan

"Di kamar saat sedang belajar aku sangat terganggu suara berisik."
```

Maka Digital Self harus mempertahankan:

- pengalaman,
- konteks,
- waktu,
- orang,
- kejadian,
- persepsi,
- emosi,
- tindakan,
- hasil,
- hubungan antar pengalaman,
- serta perubahan internal state.

---

# 3. Core Vision

## 3.1 Bukan "database tentang manusia"

Sistem tidak bertujuan membuat profil statis.

Bukan:

```text
Luki
├── suka teknologi
├── suka coding
├── tidak suka X
└── orangnya seperti Y
```

Melainkan:

```text
                    EXPERIENCE
                         │
              ┌──────────┼──────────┐
              ↓          ↓          ↓
           EVENT       EMOTION    CONTEXT
              │          │          │
              └──────┬───┴──────────┘
                     ↓
                ASSOCIATION
                     │
                     ↓
                MEMORY NETWORK
                     │
              ┌──────┴──────┐
              ↓             ↓
           PATTERN       BELIEF
              │             │
              └──────┬──────┘
                     ↓
                 REASONING
                     │
                     ↓
                  DECISION
                     │
                     ↓
              NEW EXPERIENCE
                     │
                     └──────→ kembali ke sistem
```

Sistem bersifat **continual**.

Setiap pengalaman baru berpotensi mengubah cara sistem memahami pengalaman sebelumnya.

---

# 4. Core Principles

## 4.1 Raw Experience Is Ground Truth

Pengalaman mentah pengguna harus dipertahankan.

Contoh:

```json
{
  "raw_text": "Tadi di kantor temanku sepatunya agak bau...",
  "timestamp": "2026-10-01T..."
}
```

Interpretasi AI tidak boleh menggantikan pengalaman mentah.

Jika AI salah memahami pengalaman tersebut, data asli masih tersedia untuk diperiksa.

---

# 4.2 Interpretation Is Not Truth

LLM dapat menghasilkan interpretasi:

```text
User seemed annoyed after tripping.
```

Namun sistem tidak boleh menganggapnya sebagai fakta mutlak.

Interpretasi memiliki:

```text
confidence
source
evidence
```

Contoh:

```text
Interpretation:
    "tripping caused annoyance"

Confidence:
    0.84

Evidence:
    Experience #183
```

---

# 4.3 Memory Has Provenance

Setiap abstraksi harus dapat ditelusuri kembali ke pengalaman yang menjadi sumbernya.

Contoh:

```text
Pattern
  ↓
Association
  ↓
Memory
  ↓
Experience #183
Experience #201
Experience #244
```

Dengan demikian agent tidak hanya mengatakan:

> "Kamu biasanya seperti ini."

Tetapi secara internal dapat mengetahui:

> "Kesimpulan ini muncul dari beberapa pengalaman tertentu."

---

# 4.4 Contradictions Are Allowed

Seseorang tidak harus selalu konsisten.

Contoh:

```text
Experience #1
Noise → annoyance

Experience #2
Noise → neutral

Experience #3
Noise → annoyance
```

Sistem tidak boleh memaksa:

```text
User hates noise.
```

Sebaliknya:

```text
noise → annoyance

strength: 0.61

context:
    studying → strong
    social environment → weak
```

Kontradiksi menjadi bagian dari model.

---

# 4.5 Memory Is Contextual

Hubungan tidak selalu berlaku secara universal.

Contoh:

```text
Music → positive emotion
```

bisa berubah menjadi:

```text
Music
├── while relaxing → positive
├── while studying → neutral
└── when trying to sleep → negative
```

Karena itu context merupakan bagian fundamental dari Digital Self.

---

# 4.6 The Self Model Must Emerge

Sistem tidak boleh dimulai dengan personality JSON seperti:

```json
{
  "personality": "curious",
  "likes": ["technology"]
}
```

Sebaliknya, personality atau self-model harus muncul dari pola pengalaman.

```text
many experiences
       ↓
repeated patterns
       ↓
stable associations
       ↓
behavioral patterns
       ↓
self-model hypotheses
```

Self-model dapat berubah apabila bukti baru muncul.

---

# 5. What Digital Self Stores

Digital Self terdiri dari beberapa lapisan data.

## 5.1 Experience

Representasi pengalaman mentah.

```text
Experience
├── raw text
├── timestamp
├── context
├── participants
├── events
├── perceptions
├── thoughts
├── emotions
├── actions
└── consequences
```

---

# 5.2 Perception

Apa yang dirasakan atau diamati.

Contoh:

```text
smell
sound
visual observation
physical sensation
environment
```

Perception tidak sama dengan objective fact.

---

# 5.3 Event

Sesuatu yang terjadi.

Contoh:

```text
walked
tripped
talked
ate
coded
received message
finished task
```

---

# 5.4 Emotion / Affective State

Respons emosional.

Contoh:

```text
happy
annoyed
curious
frustrated
calm
excited
neutral
```

Besarnya respons juga dapat disimpan.

```text
emotion = annoyance
intensity = 0.65
```

---

# 5.5 Thought

Apa yang dipikirkan pengguna dalam pengalaman tersebut.

Contoh:

```text
"I should be more careful."
```

Thought berbeda dari fact.

---

# 5.6 Action

Apa yang dilakukan pengguna.

```text
walked
ignored
continued working
stopped
asked someone
```

---

# 5.7 Context

Situasi ketika pengalaman terjadi.

Contoh:

```text
location
time
people
activity
environment
current internal state
```

Context sangat penting karena reaksi terhadap kejadian dapat berubah tergantung kondisi.

---

# 5.8 Node

Node merupakan representasi elemen yang berulang atau memiliki identitas dalam memory network.

Contoh:

```text
Person
Object
Place
Event
Emotion
Concept
Action
Goal
Memory
Belief
Pattern
```

Node bukan sekadar label.

Node dapat memiliki:

```text
activation
confidence
familiarity
emotional weight
frequency
first seen
last seen
source experiences
```

---

# 5.9 Association

Association merepresentasikan hubungan antar node.

Contoh:

```text
Tripping ──causes──> Annoyance

Shoes ──has_property──> Smell

Office ──contains──> Friend

Coding ──associated_with──> Curiosity
```

Association memiliki properti dinamis:

```text
strength
confidence
frequency
positive evidence
negative evidence
recency
source experiences
```

---

# 5.10 Assembly

Tidak semua pengalaman dapat direpresentasikan secara ideal hanya dengan hubungan dua node.

Contoh:

```text
Eating rendang
at home
with mother
at night
while feeling comfortable
```

Merupakan satu konfigurasi pengalaman.

Sistem dapat menyimpan sebuah **assembly**:

```text
Assembly #21

Members:
    Rendang
    Home
    Mother
    Night
    Comfort
    Eating

Context:
    Family evening
```

Assembly membantu mempertahankan struktur pengalaman yang lebih kompleks.

---

# 6. Brain Architecture

Arsitektur utama:

```text
                         RAW EXPERIENCE
                                │
                                ▼
                           PERCEPTION
                                │
                                ▼
                     EXPERIENCE INTERPRETER
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
             EVENTS         EMOTIONS          CONCEPTS
                │               │                │
                └───────────────┼────────────────┘
                                ▼
                         MEMORY NETWORK
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
               ASSOCIATION   ASSEMBLY    EPISODE
                    │           │           │
                    └───────────┼───────────┘
                                ▼
                           ACTIVATION
                                │
                                ▼
                        INTERNAL STATE
                                │
                                ▼
                         PATTERN DETECTION
                                │
                                ▼
                           BELIEF MODEL
                                │
                                ▼
                            REASONING
                                │
                                ▼
                             DECISION
                                │
                                ▼
                         NEW EXPERIENCE
```

---

# 7. Dynamic Brain

Brain tidak dianggap sebagai graph statis.

Database mungkin memiliki:

```text
10,000 nodes
```

tetapi tidak semuanya aktif ketika reasoning.

Contoh situasi:

```text
User:
"Aku mau memutuskan apakah lanjut coding atau istirahat."
```

Sistem melakukan activation.

```text
CURRENT SITUATION
       ↓
coding
       ↓
fatigue
       ↓
past coding sessions
       ↓
sleep patterns
       ↓
previous decisions
       ↓
outcomes
```

Node yang relevan mendapatkan activation lebih tinggi.

```text
[CODING]       0.92
[FATIGUE]      0.88
[SLEEP]        0.71
[WORK]         0.64
[SHOES]        0.02
[FOOD]         0.10
```

UI kemudian dapat menampilkan:

```text
ACTIVE NETWORK
```

sementara bagian lain menjadi lebih redup.

---

# 8. Activation

Activation menentukan bagian memory mana yang sedang aktif.

Activation dapat dipengaruhi oleh:

```text
semantic relevance
recency
frequency
emotional salience
context similarity
current internal state
association strength
```

Secara konseptual:

```text
activation =
    relevance
  + recency
  + frequency
  + emotional_salience
  + contextual_similarity
  + association_strength
```

Implementasi matematis final belum dikunci pada V0.1.

---

# 9. Internal State

Digital Self memiliki keadaan internal yang berubah seiring pengalaman.

Contoh:

```text
energy
stress
curiosity
confidence
frustration
motivation
social comfort
attention
```

Contoh:

```text
Before experience:

energy       = 0.70
stress       = 0.30
curiosity    = 0.80

After difficult debugging:

energy       = 0.45
stress       = 0.70
curiosity    = 0.75
frustration  = 0.80
```

Internal state kemudian memengaruhi activation dan reasoning berikutnya.

---

# 10. Memory Consolidation

Tidak semua pengalaman memiliki bobot yang sama.

Namun semua raw experience tetap dapat disimpan.

Sistem melakukan proses consolidation:

```text
RAW EXPERIENCE
       ↓
RECENT MEMORY
       ↓
REPEATED / IMPORTANT
       ↓
STRONGER ASSOCIATION
       ↓
LONG-TERM PATTERN
```

Faktor yang dapat meningkatkan importance:

```text
repetition
emotional intensity
novelty
decision relevance
personal significance
frequency
recency
```

Memory consolidation tidak berarti menghapus pengalaman lama.

Raw experience tetap menjadi sumber bukti.

---

# 11. Learning

Learning terjadi melalui perubahan network.

Misalnya:

### Pengalaman pertama

```text
Coding → frustration

strength = 0.20
```

### Pengalaman berikutnya

```text
Coding → frustration

strength = 0.35
```

### Berkali-kali

```text
Coding → frustration

strength = 0.72
```

Namun kemudian:

```text
Coding → satisfaction
```

muncul berkali-kali.

Network dapat berubah menjadi:

```text
Coding
├── frustration
│     strength = 0.58
│
└── satisfaction
      strength = 0.46
```

Kemudian context dapat membedakan:

```text
Coding
├── difficult debugging → frustration
├── successful project → satisfaction
└── learning new concept → curiosity
```

Ini lebih mendekati **context-dependent learning** daripada sekadar preference list.

---

# 12. Decision Agent

Tahap akhir sistem adalah agent yang menggunakan brain network.

Input:

```text
Current situation
```

Proses:

```text
1. Understand current situation
2. Determine relevant context
3. Activate related memory
4. Retrieve past experiences
5. Traverse relevant associations
6. Check internal state
7. Retrieve previous decisions
8. Check patterns
9. Check contradictory evidence
10. Simulate possible outcomes
11. Reason
12. Produce response
```

Output bukan hanya:

> "Lakukan X."

Agent harus dapat memiliki reasoning berdasarkan pengalaman.

Contoh internal structure:

```text
Current situation
        ↓
Relevant memories
        ↓
Past decisions
        ↓
Observed outcomes
        ↓
Patterns
        ↓
Contradictions
        ↓
Current state
        ↓
Reasoning
```

---

# 13. Decision Provenance

Setiap keputusan agent harus dapat ditelusuri.

Contoh:

```text
Decision #42

Situation:
    Should I continue working?

Relevant memories:
    Experience #81
    Experience #103
    Experience #220

Patterns:
    prolonged work → lower concentration

Internal state:
    fatigue = 0.81

Reasoning:
    ...
```

Hal ini memungkinkan sistem mengetahui **mengapa** sebuah keputusan muncul.

---

# 14. User Interface

UI memiliki dua mode utama.

---

## 14.1 Experience Mode

Ini adalah tempat pengguna memasukkan pengalaman.

Layout:

```text
┌──────────────────────────────────────────┐
│              DIGITAL SELF                │
│                                          │
│       Brain visualization                │
│                                          │
│    ●──────●                              │
│   /       │       ●                      │
│  ●        └───────●                      │
│                                          │
│                                          │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ Tadi di kantor aku...                │ │
│ └──────────────────────────────────────┘ │
│                         [ SEND ]          │
└──────────────────────────────────────────┘
```

Setelah Send:

```text
Experience
      ↓
Brain processing
      ↓
new nodes
      ↓
new connections
      ↓
activation changes
```

UI menampilkan node baru secara animated.

---

# 15. Brain Mode

Brain Mode digunakan untuk mengeksplorasi memory network.

Fitur:

```text
zoom
pan
drag
hover
click
search
filter
timeline
activation view
context view
```

Hover node:

```text
┌─────────────────────┐
│ KESAL                │
├─────────────────────┤
│ Type: Emotion        │
│ Experiences: 17      │
│ Associations: 12     │
│ Last seen: Today     │
│ Activation: 0.84     │
└─────────────────────┘
```

Hover edge:

```text
TRIPPING ──causes──> ANNOYANCE

Strength: 0.73
Frequency: 8
Confidence: 0.81
Evidence: 8 experiences
```

Click node:

```text
Node
 ↓
Related experiences
 ↓
Related nodes
 ↓
History
```

---

# 16. Visual Language

Node dapat dibedakan berdasarkan tipe.

Contoh:

```text
Person      → node type A
Place       → node type B
Emotion     → node type C
Event       → node type D
Concept     → node type E
Memory      → node type F
Belief      → node type G
Goal        → node type H
```

Visual bukan sekadar dekorasi.

UI harus menunjukkan:

```text
activation
importance
relationship strength
recency
type
```

---

# 17. Realtime Brain Update

Ketika pengguna mengirim pengalaman:

```text
Frontend
   │
   │ experience
   ▼
FastAPI
   │
   ▼
Brain Engine
   │
   ├── interpret
   ├── retrieve
   ├── create nodes
   ├── update associations
   ├── update state
   └── calculate activation
   │
   ▼
WebSocket Event
   │
   ▼
Frontend
   │
   ├── create node animation
   ├── create edges
   ├── update active nodes
   └── update UI
```

Hasilnya pengguna dapat **melihat brain berkembang ketika memasukkan pengalaman**.

---

# 18. Technology Stack

## Brain

```text
Python 3.12+
```

Dipilih karena project membutuhkan eksperimen:

- LLM
- embeddings
- NLP
- graph processing
- numerical computation
- machine learning

---

## API

```text
FastAPI
```

Digunakan sebagai interface antara frontend dan brain engine.

---

## Database

```text
PostgreSQL
```

Menyimpan:

```text
experiences
nodes
associations
memories
assemblies
internal states
patterns
beliefs
decisions
```

---

## Vector Search

```text
pgvector
```

Digunakan untuk semantic retrieval.

Contoh:

```text
Current situation
       ↓
embedding
       ↓
vector search
       ↓
similar experiences
```

---

## Graph Processing

Prototype:

```text
NetworkX
```

Graph database khusus belum diperlukan pada tahap awal.

Kita terlebih dahulu menguji model brain-nya.

---

## LLM

```text
OpenAI API
```

Digunakan untuk:

```text
experience interpretation
entity extraction
event extraction
emotion interpretation
semantic understanding
reasoning
```

LLM **bukan database** dan bukan sumber kebenaran utama.

---

## Frontend

```text
Next.js
TypeScript
Tailwind CSS
React Flow
```

Digunakan untuk:

```text
Experience Mode
Brain Mode
interactive graph
node inspection
memory exploration
```

---

## Infrastructure

```text
Docker
Docker Compose
```

Digunakan untuk local development.

---

# 19. Proposed System Architecture

```text
digital-self
│
├─────────────────────────────────────┐
│                                     │
▼                                     ▼
FRONTEND                           BACKEND
Next.js                            FastAPI
│                                     │
│                                     ▼
│                               BRAIN ENGINE
│                                     │
│              ┌──────────────────────┼──────────────────────┐
│              │                      │                      │
│              ▼                      ▼                      ▼
│          EXPERIENCE              MEMORY                REASONING
│              │                      │                      │
│              ▼                      ▼                      ▼
│          INTERPRETER           ASSOCIATION             DECISION
│                                     │
│                                     ▼
│                                ACTIVATION
│                                     │
│                                     ▼
│                                INTERNAL STATE
│                                     │
└──────────────────────┬──────────────┘
                       │
                       ▼
                  PostgreSQL
                    + pgvector
                       │
                       ▼
                  OpenAI API
```

---

# 20. Data Flow

## Experience ingestion

```text
User input
    ↓
Raw experience saved
    ↓
LLM interpretation
    ↓
Candidate concepts/events/emotions
    ↓
Embedding generation
    ↓
Existing node retrieval
    ↓
Merge OR create node
    ↓
Create/update associations
    ↓
Update assembly
    ↓
Update internal state
    ↓
Calculate activation
    ↓
Return brain update
```

---

# 21. Data Integrity Model

Ada tiga tingkat kepastian.

### Level 1: Raw

```text
"I felt annoyed after tripping."
```

Fakta bahwa pengguna menulis kalimat tersebut disimpan secara literal.

### Level 2: Interpretation

```text
tripping → annoyance
```

Memiliki confidence.

### Level 3: Pattern

```text
Physical disruption often correlates with annoyance.
```

Memerlukan bukti dari beberapa experiences.

Semakin tinggi tingkat abstraksi, semakin penting provenance dan confidence.

---

# 22. Important Distinction

Sistem harus membedakan:

```text
WHAT HAPPENED
```

dengan:

```text
WHAT THE AI THINKS HAPPENED
```

dan:

```text
WHAT THE SYSTEM LEARNED FROM REPEATED EXPERIENCES
```

Ketiganya tidak boleh dicampur.

---

# 23. Security & Privacy

Karena sistem menyimpan pengalaman pribadi, privacy merupakan bagian fundamental.

Minimal:

```text
local development by default
environment variables for secrets
no API keys in frontend
database access control
authentication
encrypted transport
audit trail
```

Raw experience harus diperlakukan sebagai data sensitif.

---

# 24. Non-Goals

Pada tahap awal project ini **bukan** bertujuan untuk:

- membuat conscious AI,
- membuat manusia digital secara literal,
- mengklaim bahwa sistem memiliki perasaan biologis,
- meniru struktur biologis otak secara persis,
- membuat diagnosis psikologis pengguna,
- menggantikan keputusan manusia,
- membuat personality statis berdasarkan beberapa chat,
- membangun AGI.

Project ini adalah **computational model inspired by memory, association, context, internal state, and learning**.

---

# 25. Development Roadmap

## Phase 0 — Brain Model

Definisikan:

```text
Experience
Node
Association
Assembly
Internal State
Activation
```

Output:

```text
Brain Data Model v0.1
```

---

## Phase 1 — Brain Core

Implement:

```text
experience ingestion
node creation
association creation
activation
```

Belum menggunakan LLM kompleks.

Target:

```text
1 experience
→
structured memory network
```

---

## Phase 2 — Persistent Memory

Implement:

```text
PostgreSQL
pgvector
repository layer
```

Target:

```text
brain survives application restart
```

---

## Phase 3 — LLM Interpretation

Implement:

```text
experience
→
events
→
concepts
→
emotions
→
context
→
actions
```

---

## Phase 4 — Associative Memory

Implement:

```text
semantic retrieval
association strengthening
association weakening
recency
frequency
contradiction
```

---

## Phase 5 — Internal State

Implement:

```text
energy
stress
curiosity
confidence
motivation
frustration
attention
```

---

## Phase 6 — Consolidation

Implement:

```text
experience
→
repeated evidence
→
pattern
→
belief hypothesis
```

---

## Phase 7 — Reasoning Agent

Implement:

```text
current situation
→
memory activation
→
relevant experiences
→
patterns
→
state
→
reasoning
→
decision
```

---

## Phase 8 — Brain UI

Implement:

```text
Experience Mode
Brain Mode
node animation
edge animation
activation visualization
memory exploration
```

---

## Phase 9 — Continuous Digital Self

Final loop:

```text
                 ┌─────────────────┐
                 │     EXPERIENCE  │
                 └────────┬────────┘
                          ↓
                    PERCEPTION
                          ↓
                       MEMORY
                          ↓
                     ASSOCIATION
                          ↓
                    INTERNAL STATE
                          ↓
                       PATTERN
                          ↓
                       BELIEF
                          ↓
                      REASONING
                          ↓
                       DECISION
                          ↓
                 ┌────────┴────────┐
                 │  NEW EXPERIENCE │
                 └─────────────────┘
```

Sistem terus berkembang selama digunakan.

---

# 26. MVP Definition

MVP **bukan** agent yang sudah bisa berpikir seperti manusia.

MVP adalah:

> Pengguna memasukkan pengalaman dan sistem mampu mengubahnya menjadi memory network yang dapat berkembang dari pengalaman berikutnya.

Contoh:

```text
INPUT 1

"Aku coding Go tadi dan bingung memahami interface."
```

Menjadi:

```text
Go
 │
 └── Interface
       │
       └── Confusion
```

Kemudian:

```text
INPUT 2

"Hari ini akhirnya aku paham interface setelah mencoba contoh kecil."
```

Network berkembang:

```text
Go
 │
 └── Interface
       ├── Confusion
       │
       └── Understanding
```

Kemudian:

```text
INPUT 3

"Aku lebih mudah memahami konsep kalau langsung membuat contoh."
```

Muncul hubungan baru:

```text
Hands-on Practice
       │
       └── Understanding
```

Setelah cukup banyak evidence:

```text
Hands-on Practice
        ↓
higher probability of understanding
```

Sistem mulai memiliki **pattern**, bukan sekadar catatan.

---

# 27. Definition of Success

Digital Self dianggap berhasil pada tahap awal apabila:

### Memory

- mampu menyimpan raw experience;
- mampu menghubungkan experience dengan entities/events/emotions;
- mampu mempertahankan provenance.

### Association

- mampu membuat hubungan;
- mampu memperkuat hubungan berdasarkan evidence;
- mampu menangani contradictory evidence.

### Context

- mampu membedakan pola berdasarkan konteks;
- tidak membuat generalisasi terlalu cepat.

### State

- internal state berubah berdasarkan experience;
- state memengaruhi activation/reasoning.

### Reasoning

- mampu mengambil relevant past experiences;
- mampu menggunakan pattern dan state;
- mampu menunjukkan evidence yang mendasari reasoning.

### Visualization

- brain network dapat divisualisasikan;
- node baru muncul saat experience diproses;
- active memories dapat terlihat;
- user dapat menelusuri node kembali ke pengalaman sumber.

---

# 28. Fundamental Philosophy

Digital Self tidak mencoba membuat:

> **"AI yang tahu siapa Luki."**

Digital Self mencoba membuat:

> **"Sistem yang terus membangun pemahamannya tentang Luki dari pengalaman Luki."**

Perbedaan ini sangat penting.

Sistem tidak diberikan jawaban final tentang siapa seseorang.

Sistem diberikan:

```text
experiences
```

dan membiarkan:

```text
memories
→ associations
→ patterns
→ beliefs
→ self-model
```

berkembang secara bertahap.

---

# 29. First Technical Milestone

Sebelum membangun UI atau agent, project harus mencapai milestone berikut:

```text
Raw Experience
       ↓
Structured Experience
       ↓
Nodes
       ↓
Associations
       ↓
Activation
       ↓
Brain State
```

Contoh:

```text
User:

"Tadi aku kesandung di kantor dan lumayan kesal."
```

Output internal:

```text
Experience #001

Context:
    Office

Event:
    Tripped

Emotion:
    Annoyance
    intensity = 0.65

Nodes:
    Office
    Tripping
    Annoyance

Associations:
    Office ──context──> Tripping
    Tripping ──causes──> Annoyance

Activation:
    Tripping = 0.91
    Annoyance = 0.82
    Office = 0.54
```

Ini adalah **sel pertama dari Digital Self**.

Setelah sel ini benar, barulah kita membangun sistem yang lebih besar.

---

# 30. Project Principle

> **Don't program the personality. Build the memory system from which a model of the personality can emerge.**

Aturan ini menjadi prinsip utama seluruh project.

Kita tidak membuat:

```text
if user == Luki:
    personality = ...
```

Kita membuat:

```text
experience
    ↓
memory
    ↓
association
    ↓
pattern
    ↓
self-model
```

Dan setiap kesimpulan harus tetap dapat ditelusuri kembali ke pengalaman yang membentuknya.

----------------------------------------------------------------------------------------------------
VERSI 2 REVISI DARI VERSI DIAATAS
----------------------------------------------------------------------------------------------------

# Digital Self — PRD V2 Revision

> **Revision of PRD V1 — From Conceptual Architecture to Formal, Testable System Design**

**Status:** Architecture / Pre-Implementation  
**Version:** 0.2  
**Based on:** Digital Self PRD V1

---

# 1. Purpose of This Revision

PRD V1 mendefinisikan visi utama Digital Self:

> Sebuah computational second version of the self yang membangun pemahaman tentang seseorang berdasarkan pengalaman yang dikumpulkan secara terus-menerus.

V1 sudah mendefinisikan:

- Experience
- Node
- Association
- Assembly
- Memory
- Activation
- Internal State
- Pattern
- Belief
- Reasoning
- Decision
- Brain Visualization

Namun agar sistem dapat benar-benar dibangun, V2 menambahkan lapisan formal untuk:

1. data schema,
2. relationship taxonomy,
3. temporal model,
4. learning mathematics,
5. correction,
6. evaluation,
7. failure handling,
8. privacy and security,
9. memory lifecycle,
10. reasoning policy,
11. cold start,
12. identity/versioning,
13. observability,
14. multilingual and multimodal support.

V2 **tidak mengubah visi dasar Digital Self**.

V2 memperjelas bagaimana visi tersebut dapat direalisasikan secara teknis.

---

# 2. Core Design Rule

Prinsip utama tetap:

> **Don't program the personality. Build the memory system from which a model of the personality can emerge.**

Namun V2 menambahkan aturan kedua:

> **Every abstraction must be traceable, correctable, measurable, and reversible.**

Artinya setiap:

- node,
- association,
- pattern,
- belief,
- decision

harus dapat diketahui:

```text
Where did this come from?
Why does the system believe it?
How confident is it?
Can the user correct it?
Can it be reproduced?
Can it be reverted?
```

---

# 3. Formal Cognitive Layers

Digital Self menggunakan hierarchy berikut:

```text
RAW EXPERIENCE
       │
       ▼
PERCEPTION
       │
       ▼
EVENT / ENTITY / EMOTION / THOUGHT / ACTION
       │
       ▼
EPISODIC MEMORY
       │
       ▼
ASSOCIATION
       │
       ▼
ASSEMBLY
       │
       ▼
PATTERN
       │
       ▼
BELIEF / HYPOTHESIS
       │
       ▼
SELF MODEL
       │
       ▼
REASONING
       │
       ▼
DECISION
       │
       ▼
OUTCOME
       │
       └──────────────► NEW EXPERIENCE
```

Semakin ke bawah, semakin abstrak.

Semakin abstrak, semakin tinggi kebutuhan terhadap:

- evidence,
- confidence,
- provenance,
- validation.

---

# 4. Immutable vs Mutable Data

Sistem harus membedakan data yang tidak boleh berubah dari data yang memang dapat berkembang.

## 4.1 Immutable

Raw experience:

```text
raw_text
original_timestamp
original_source
```

Contoh:

```text
"Tadi aku kesandung di kantor dan lumayan kesal."
```

Versi asli harus tetap tersedia.

---

## 4.2 Mutable

Hal-hal berikut dapat berubah:

```text
interpretation
confidence
association strength
activation
pattern
belief
self-model
internal state
```

Contoh:

```text
Interpretation v1:
    "User was angry"

Correction:
    "Actually I was only annoyed."

Interpretation v2:
    "User was mildly annoyed"
```

Raw experience tidak perlu diubah.

---

# 5. Formal Experience Schema

Experience minimal memiliki:

```text
Experience
├── id
├── raw_text
├── created_at
├── occurred_at
├── source
├── context
├── participants
├── observations
├── events
├── thoughts
├── emotions
├── actions
├── consequences
└── metadata
```

Perbedaan penting:

```text
created_at
```

adalah waktu ketika pengguna mencatat pengalaman.

Sedangkan:

```text
occurred_at
```

adalah waktu ketika pengalaman sebenarnya terjadi.

Contoh:

```text
occurred_at:
2026-09-30 10:00

created_at:
2026-10-01 18:00
```

Dengan demikian sistem dapat menjawab pertanyaan temporal seperti:

> "Apa yang terjadi kemarin?"

tanpa menyamakan waktu kejadian dengan waktu pencatatan.

---

# 6. Temporal Model

Setiap event dapat memiliki:

```text
start_time
end_time
duration
sequence
```

Contoh:

```text
Event A
started: 10:00
ended: 10:05

Event B
started: 10:06
ended: 10:07
```

Relationship temporal:

```text
before
after
during
overlaps
starts
ends
```

Contoh:

```text
Coding
    ──before──>
Break

Trip
    ──before──>
Annoyance
```

Hal ini memungkinkan sistem memahami urutan kejadian, bukan hanya co-occurrence.

---

# 7. Relationship Taxonomy

Association tidak boleh hanya memiliki:

```text
from
to
strength
```

Relationship harus memiliki tipe.

Initial taxonomy:

```text
causes
correlates_with
co_occurs_with

before
after
during
overlaps

part_of
contains

instance_of
is_a
has_property

located_at
occurred_at
involves

similar_to
contradicts

supports
weakens

associated_with
```

Contoh:

```text
Tripping
    ──causes──>
Annoyance
```

berbeda dengan:

```text
Office
    ──co_occurs_with──>
Tripping
```

dan berbeda lagi dengan:

```text
Shoes
    ──has_property──>
Smell
```

---

# 8. Correlation vs Causation

Sistem **tidak boleh otomatis menganggap association sebagai causation**.

Jika:

```text
A
+
B
```

sering muncul bersama, sistem awalnya hanya boleh mengatakan:

```text
A ──co_occurs_with──> B
```

Untuk memperoleh:

```text
A ──causes──> B
```

dibutuhkan evidence yang lebih kuat atau explicit user statement.

Contoh:

```text
User:
"Aku kesandung karena lantainya licin."
```

Ini memberikan explicit causal statement:

```text
Slippery floor
    ──causes──>
Tripping
```

Namun sistem tetap menyimpan:

```text
causal_confidence
```

bukan menjadikannya kebenaran absolut.

---

# 9. Entity Resolution

Problem:

```text
"kantor"
"office"
"tempat kerja"
"kantorku"
```

Apakah semuanya node berbeda?

Tidak selalu.

Sistem membutuhkan entity resolution.

Conceptually:

```text
Mention
    ↓
Candidate nodes
    ↓
Similarity
    ↓
Context
    ↓
Existing relationships
    ↓
Decision
```

Contoh:

```text
"kantor"
```

dapat dipetakan ke:

```text
Node #17
canonical_name = "Office"
```

tetapi:

```text
"kantor baru"
```

dapat menjadi node berbeda jika konteks menunjukkan lokasi berbeda.

---

# 10. Node Identity

Node memiliki:

```text
id
canonical_name
type
aliases
embedding
created_at
updated_at
```

Contoh:

```text
Node #17

canonical_name:
    Office

aliases:
    kantor
    tempat kerja
    office

type:
    place
```

Node identity tidak boleh hanya bergantung pada string matching.

---

# 11. Association Data Model

Association minimal:

```text
Association
├── id
├── source_node
├── target_node
├── type
├── strength
├── confidence
├── frequency
├── positive_evidence
├── negative_evidence
├── first_observed
├── last_observed
└── source_experiences
```

Dengan demikian:

```text
Tripping
   │
   │ causes
   │
   ▼
Annoyance
```

memiliki sejarah.

---

# 12. Association Learning

Association strength harus memiliki update rule yang jelas.

Initial conceptual model:

### Positive evidence

```text
s_new =
    s_old + α × w × (1 - s_old)
```

### Negative evidence

```text
s_new =
    s_old - β × w × s_old
```

### Time decay

```text
s_decay =
    s × exp(-λ × Δt)
```

Keterangan:

```text
s  = current strength
α  = positive learning rate
β  = negative learning rate
w  = evidence weight
λ  = decay rate
Δt = time elapsed
```

Parameter tersebut tidak dianggap final.

V2 hanya menetapkan bahwa learning harus memiliki mekanisme matematis yang dapat diuji.

---

# 13. Evidence Weight

Tidak semua evidence memiliki bobot sama.

Contoh:

```text
Explicit user statement
    weight = high

Direct repeated experience
    weight = high

LLM interpretation
    weight = medium/low

Weak semantic similarity
    weight = low
```

Sistem tidak boleh memperlakukan:

> "LLM menduga..."

sama dengan:

> "User secara eksplisit mengatakan..."

---

# 14. Confidence Model

Confidence tidak sama dengan strength.

Contoh:

```text
Association:
    Coding → Frustration

Strength:
    0.74

Confidence:
    0.53
```

Artinya:

- hubungan tersebut cukup sering muncul,
- tetapi evidence belum cukup untuk sangat yakin terhadap generalisasi tersebut.

Confidence dapat dipengaruhi oleh:

```text
source reliability
evidence count
evidence consistency
contradiction
LLM uncertainty
user confirmation
```

---

# 15. Contradiction Model

Sistem harus dapat menyimpan:

```text
positive evidence
negative evidence
```

Contoh:

```text
Coding → Frustration
positive evidence = 8

Coding → Satisfaction
positive evidence = 5
```

Tidak boleh dipaksa menjadi satu kesimpulan.

Context dapat digunakan untuk menjelaskan kontradiksi:

```text
Coding
├── difficult debugging
│      └── frustration
│
├── successful project
│      └── satisfaction
│
└── learning new concept
       └── curiosity
```

---

# 16. Pattern Formation

Pattern tidak boleh terbentuk hanya dari satu experience.

Minimal conceptual rule:

```text
Experience
    ↓
Observation
    ↓
Repeated evidence
    ↓
Association
    ↓
Pattern candidate
    ↓
Validation
    ↓
Pattern
```

Pattern harus memiliki:

```text
evidence_count
confidence
contexts
supporting_experiences
contradicting_experiences
```

---

# 17. Belief Formation

Belief memiliki tingkat abstraksi lebih tinggi daripada pattern.

Contoh:

```text
Pattern:
Hands-on experimentation frequently precedes understanding.

↓

Belief hypothesis:
User tends to understand technical concepts better through practice.
```

Belief harus tetap dianggap sebagai:

```text
hypothesis
```

bukan immutable fact.

---

# 18. Human Correction Layer

Pengguna harus dapat mengoreksi sistem.

Contoh:

```text
AI:
"You were angry."

User:
"No. I was only annoyed."
```

Sistem:

```text
Raw Experience
    ↓
Interpretation v1
    ↓
USER CORRECTION
    ↓
Interpretation v2
```

Correction menjadi evidence baru.

---

# 19. Correction Types

User dapat:

```text
correct
delete
merge
split
confirm
reject
modify
```

Contoh:

### Merge

```text
Office
kantor
```

→ same node.

### Split

```text
Friend
```

ternyata merujuk kepada dua orang berbeda.

```text
Friend A
Friend B
```

---

# 20. Correction Learning

Correction tidak hanya memperbaiki satu record.

Jika user berkali-kali mengoreksi:

```text
LLM interpretation:
"angry"

User:
"usually I'm annoyed, not angry"
```

sistem dapat menurunkan confidence terhadap interpretasi serupa.

Dengan demikian:

```text
Correction
    ↓
Model calibration
```

Namun koreksi tidak boleh otomatis mengubah semua historical data tanpa provenance.

---

# 21. Activation Model

Activation merupakan kombinasi beberapa faktor:

```text
semantic relevance
recency
frequency
emotional salience
context similarity
association strength
internal state
```

Conceptually:

```text
activation =
    f(
        relevance,
        recency,
        frequency,
        emotional_salience,
        context_similarity,
        association_strength,
        internal_state
    )
```

Activation harus:

```text
normalized
bounded
decaying
context-sensitive
```

Nilai final akan ditentukan melalui eksperimen.

---

# 22. Spreading Activation

Ketika sebuah node aktif:

```text
Current situation
        ↓
Node A
        ↓
Node B
        ↓
Node C
```

activation dapat menyebar melalui association.

Namun spreading activation harus memiliki:

```text
depth limit
decay
threshold
inhibition
```

agar seluruh graph tidak menjadi aktif sekaligus.

---

# 23. Inhibition

Tidak semua association yang relevan harus ikut aktif.

Contoh:

```text
Current situation:
coding + fatigue
```

Memory:

```text
coding
```

aktif.

Tetapi:

```text
coding + childhood memory
```

mungkin tidak relevan.

Maka sistem membutuhkan mechanism untuk menekan activation yang tidak relevan.

Tujuan:

```text
relevant memories → stronger
irrelevant memories → weaker
```

---

# 24. Memory Lifecycle

Memory dibagi menjadi beberapa state:

```text
HOT
WARM
COLD
ARCHIVED
```

### Hot

Recent atau sedang aktif.

### Warm

Sering digunakan atau memiliki relevance.

### Cold

Jarang digunakan tetapi tetap tersedia.

### Archived

Tidak aktif dalam retrieval normal tetapi tidak dihapus dari raw history.

---

# 25. Long-Term Storage

Raw experience tidak otomatis dihapus hanya karena memory sudah lama.

Namun retrieval layer dapat menggunakan:

```text
hot memory
+
semantic retrieval
+
temporal retrieval
+
importance
```

daripada selalu membaca seluruh database.

---

# 26. Graph Growth Control

Graph dapat berkembang sangat besar.

Maka diperlukan:

```text
deduplication
entity resolution
edge threshold
node threshold
memory consolidation
archival
```

Tujuannya bukan menghapus pengalaman.

Tujuannya:

```text
raw history = complete
active graph = manageable
```

---

# 27. Cold Start

Ketika:

```text
experience_count = 0
```

Digital Self tidak boleh berpura-pura sudah mengenal user.

Initial state:

```text
knowledge = empty
patterns = empty
beliefs = empty
confidence = low
```

Pattern formation harus menunggu evidence yang cukup.

---

# 28. Cold Start Strategy

Pada awal penggunaan:

```text
Experience
    ↓
Memory
    ↓
Association
```

tetapi belum:

```text
Memory
    ↓
Strong personality conclusion
```

Sistem harus memiliki threshold untuk pembentukan pattern.

Contoh konseptual:

```text
1 occurrence
    → observation

several occurrences
    → pattern candidate

consistent evidence
    → pattern

strong evidence + validation
    → belief hypothesis
```

Angka final harus ditentukan melalui evaluation.

---

# 29. Reasoning Policy

Reasoning harus membedakan:

```text
FACT
OBSERVATION
PATTERN
BELIEF
HYPOTHESIS
INFERENCE
```

Contoh:

```text
FACT:
User wrote that they were annoyed.

OBSERVATION:
Tripping and annoyance occurred together.

PATTERN:
Similar situations have repeatedly produced annoyance.

HYPOTHESIS:
Physical disruption may commonly affect the user's mood.

INFERENCE:
This situation may result in annoyance.
```

Agent tidak boleh menyajikan inference sebagai fact.

---

# 30. Evidence-Based Reasoning

Setiap reasoning penting harus memiliki internal evidence chain:

```text
Decision
   ↓
Reasoning
   ↓
Pattern
   ↓
Associations
   ↓
Experiences
```

Contoh:

```text
Decision #42

Relevant pattern:
"Long uninterrupted work sessions
have frequently preceded lower concentration."

Evidence:
Experience #18
Experience #51
Experience #92
```

---

# 31. Outcome Learning

Decision tidak berhenti setelah output.

Jika agent merekomendasikan atau mensimulasikan sebuah decision:

```text
Decision
    ↓
Outcome
    ↓
Compare expected vs actual
    ↓
Learning
```

Contoh:

```text
Expected:
Continue working → productivity

Actual:
Continue working → poor concentration
```

Evidence tersebut dapat memengaruhi future reasoning.

---

# 32. Counterfactual Reasoning

Pada tahap lanjut sistem dapat membandingkan:

```text
Option A
Option B
```

berdasarkan historical evidence.

Namun counterfactual tetap merupakan simulation, bukan fakta.

Output harus memiliki uncertainty.

---

# 33. Evaluation Framework

Project membutuhkan evaluation sejak awal.

Tidak cukup:

> "Kayaknya AI-nya makin pintar."

---

# 34. Extraction Evaluation

Untuk experience interpretation:

```text
Entity extraction
Event extraction
Emotion extraction
Action extraction
Context extraction
```

Metric:

```text
Precision
Recall
F1
```

---

# 35. Retrieval Evaluation

Untuk memory retrieval:

```text
Precision@K
Recall@K
MRR
```

Pertanyaan:

> Apakah memory yang relevan benar-benar muncul?

---

# 36. Confidence Evaluation

Confidence harus dibandingkan dengan actual correctness.

Metric yang dapat digunakan:

```text
calibration error
Brier score
confidence distribution
```

Tujuan:

```text
high confidence
    ≈
high probability of correctness
```

---

# 37. Provenance Evaluation

Setiap abstraction harus memiliki provenance.

Metric:

```text
provenance completeness
```

Pertanyaan:

> Berapa banyak pattern/belief yang dapat ditelusuri kembali ke evidence?

---

# 38. Stability Evaluation

Pattern tidak boleh berubah secara liar.

Test:

```text
same evidence
→
same model
```

dan:

```text
small new evidence
→
reasonable update
```

Bukan:

```text
one new sentence
→
complete personality change
```

---

# 39. Overgeneralization Evaluation

Test:

```text
1 unusual experience
```

dan pastikan sistem tidak langsung membuat:

```text
permanent personality trait
```

---

# 40. Synthetic Experience Dataset

Sebelum menggunakan pengalaman pribadi sebagai satu-satunya test, buat dataset sintetis.

Contoh:

```text
Experience 1:
User enjoys coding when building projects.

Experience 2:
User becomes frustrated during difficult debugging.

Experience 3:
User enjoys solving the bug after understanding it.
```

Expected graph dapat didefinisikan secara manual.

Kemudian sistem dibandingkan dengan expected output.

---

# 41. Longitudinal Evaluation

Dataset harus memiliki urutan waktu:

```text
Day 1
Day 2
Day 10
Day 30
Day 100
```

Tujuannya menguji:

```text
learning
decay
contradiction
pattern formation
memory stability
```

---

# 42. Failure Modes

Digital Self harus secara eksplisit mengantisipasi:

```text
LLM hallucination
false causality
overgeneralization
duplicate nodes
graph explosion
incorrect entity resolution
feedback loops
memory contamination
confidence inflation
retrieval failure
```

---

# 43. Failure: False Causality

Problem:

```text
A and B happened together
```

AI menyimpulkan:

```text
A caused B
```

Mitigation:

```text
default relationship = association/co-occurrence
causal relationship requires stronger evidence
```

---

# 44. Failure: Feedback Loop

Problem:

```text
Wrong pattern
    ↓
retrieval
    ↓
reasoning
    ↓
new interpretation
    ↓
reinforces wrong pattern
```

Mitigation:

```text
provenance
negative evidence
confidence decay
human correction
independent evidence
```

---

# 45. Failure: Graph Explosion

Problem:

```text
Every sentence
→
10 nodes
→
50 edges
```

setelah ribuan experience graph menjadi tidak terkendali.

Mitigation:

```text
entity resolution
deduplication
association thresholds
consolidation
archival
```

---

# 46. Failure: Confidence Inflation

Sistem tidak boleh:

```text
more mentions
=
absolute truth
```

Repeated LLM hallucinations tidak boleh dianggap sebagai independent evidence.

Evidence harus mempertimbangkan source independence.

---

# 47. Privacy Architecture

Karena Digital Self berisi data personal, privacy bukan fitur tambahan.

Privacy harus menjadi architectural constraint.

Minimal:

```text
authentication
authorization
encrypted transport
secret management
database protection
audit logs
data export
data deletion
```

---

# 48. Local-First Direction

Architecture harus memungkinkan:

```text
local database
local brain engine
optional cloud LLM
```

sehingga pengguna dapat memilih:

```text
fully local
hybrid
cloud
```

Tahap awal tidak harus langsung mendukung semua mode, tetapi architecture tidak boleh mengunci project ke cloud secara permanen.

---

# 49. Data Ownership

Model Digital Self harus dianggap sebagai data milik user.

User harus memiliki kemampuan:

```text
export
backup
restore
delete
inspect
correct
```

---

# 50. Audit Trail

Perubahan penting harus dapat dilacak.

Contoh:

```text
Association strength

0.42
 ↓
0.51
 ↓
0.64
 ↓
0.48
```

System harus dapat menjelaskan:

```text
when
why
which evidence
which algorithm
```

yang menyebabkan perubahan.

---

# 51. Versioning

Interpretation dapat memiliki versi:

```text
Interpretation v1
Interpretation v2
Interpretation v3
```

Association dapat memiliki history.

Self-model juga dapat memiliki snapshot:

```text
Self Model
├── 2026-10
├── 2026-11
├── 2027-01
└── ...
```

Dengan demikian Digital Self dapat menjawab konsep:

> "Bagaimana sistem memahami diriku pada waktu tertentu?"

---

# 52. Identity Over Time

Digital Self tidak menganggap:

```text
Luki 2026
=
Luki 2028
```

secara sempurna.

Sebaliknya:

```text
Self Model @ T1
        ↓
experiences
        ↓
Self Model @ T2
        ↓
experiences
        ↓
Self Model @ T3
```

Identity merupakan sesuatu yang berkembang.

---

# 53. Observability

Developer harus memiliki debug interface.

Minimal:

```text
Experience inspector
Node inspector
Association inspector
Activation inspector
Reasoning trace
Provenance viewer
Correction history
State timeline
```

Contoh:

```text
WHY IS THIS NODE ACTIVE?

Node:
    Coding

Activation:
    0.89

Reasons:
    semantic relevance = 0.91
    recency = 0.70
    frequency = 0.83
    context similarity = 0.94
```

---

# 54. Replay System

Developer harus dapat mengambil satu experience dan menjalankan ulang pipeline:

```text
raw experience
    ↓
interpretation
    ↓
node resolution
    ↓
association update
    ↓
activation
    ↓
state update
```

Tujuan:

```text
debugging
testing
reproducibility
```

---

# 55. Language Model

Digital Self harus mendukung natural language.

Bahasa tidak boleh menjadi identity layer.

Conceptual architecture:

```text
Indonesian
English
mixed language
      ↓
semantic representation
      ↓
canonical concepts
```

Contoh:

```text
"kantor"
"office"
"tempat kerja"
```

dapat mengarah ke canonical concept yang sama jika context mendukung.

---

# 56. Multimodal Direction

Future input dapat mencakup:

```text
text
voice
image
document
sensor/context data
```

Namun semua input akhirnya harus masuk ke model Experience yang sama.

```text
Text ────────┐
Voice ───────┤
Image ───────┤
Document ────┤
              ▼
         EXPERIENCE
```

Multimodal bukan architecture yang berbeda.

---

# 57. Ethical Boundary

Digital Self tidak boleh mengklaim:

```text
"this is exactly what you feel"
```

melainkan:

```text
"based on available evidence,
the system estimates..."
```

Sistem juga tidak boleh menyamakan:

```text
computational emotional state
```

dengan:

```text
biological human emotion
```

Internal state adalah model komputasional.

---

# 58. Dependency and Human Agency

Digital Self dirancang untuk membantu reasoning pengguna, bukan mengambil alih kehidupan pengguna.

Agent harus dapat membedakan:

```text
memory retrieval
```

dengan:

```text
decision recommendation
```

dan:

```text
final human decision
```

Human remains the final decision maker.

---

# 59. Security Threat Model

Threat model minimal:

```text
Threat
├── unauthorized access
├── database theft
├── API key leakage
├── malicious prompt injection
├── malicious imported memories
├── accidental exposure
└── compromised integrations
```

Setiap threat nantinya memiliki:

```text
risk
impact
mitigation
test
```

---

# 60. V2 Architecture

Setelah revisi, architecture menjadi:

```text
                         USER EXPERIENCE
                                │
                                ▼
                         RAW EXPERIENCE
                                │
                         [IMMUTABLE]
                                │
                                ▼
                         INTERPRETATION
                                │
                       [VERSIONED + CONFIDENCE]
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
          ENTITY              EVENT             EMOTION
             │                  │                  │
             └──────────────────┼──────────────────┘
                                ▼
                         EPISODIC MEMORY
                                │
                                ▼
                         ASSOCIATION LAYER
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
                 TEMPORAL   CONTEXTUAL   SEMANTIC
                 RELATIONS   RELATIONS   RELATIONS
                    │           │           │
                    └───────────┼───────────┘
                                ▼
                            ASSEMBLY
                                │
                                ▼
                           ACTIVATION
                                │
                      ┌─────────┴─────────┐
                      ▼                   ▼
                INTERNAL STATE       RETRIEVAL
                      │                   │
                      └─────────┬─────────┘
                                ▼
                          PATTERN ENGINE
                                │
                                ▼
                         BELIEF / HYPOTHESIS
                                │
                                ▼
                            SELF MODEL
                                │
                                ▼
                           REASONING
                                │
                                ▼
                            DECISION
                                │
                                ▼
                             OUTCOME
                                │
                                └──────────────► NEW EXPERIENCE
```

---

# 61. Revised Definition of Digital Self

Digital Self adalah:

> **A persistent, evidence-based, associative computational model of an individual's lived experiences, internal states, memories, patterns, and evolving self-model, capable of retrieving and reasoning over those experiences while preserving uncertainty, provenance, contradiction, and user correction.**

Dalam bahasa sederhana:

> **Kita tidak membuat AI yang diberi tahu siapa dirimu. Kita membuat sistem yang mengumpulkan pengalamanmu, membangun hubungan dari pengalaman tersebut, menemukan pola secara bertahap, mengingat bahwa pola itu bisa salah, dan menggunakan seluruh proses tersebut untuk membentuk versi digital yang terus berkembang dari dirimu.**

---

# 62. V2 Definition of Done

Digital Self V2 dianggap memiliki fondasi yang cukup apabila:

```text
[ ] Raw experience immutable
[ ] Experience schema formal
[ ] Temporal model implemented
[ ] Relationship taxonomy defined
[ ] Entity resolution implemented
[ ] Association update rule implemented
[ ] Decay implemented
[ ] Activation implemented
[ ] Confidence model implemented
[ ] Contradiction handling implemented
[ ] Human correction implemented
[ ] Provenance implemented
[ ] Pattern threshold defined
[ ] Synthetic evaluation dataset exists
[ ] Retrieval evaluated
[ ] Extraction evaluated
[ ] Failure modes tested
[ ] Privacy architecture defined
[ ] Audit trail implemented
[ ] Versioning implemented
[ ] Debug/replay system implemented
```

---

# 63. Next Implementation Step

Setelah PRD V2 ini, **belum langsung membuat seluruh aplikasi**.

Urutan implementasi:

```text
1. Brain Data Model
        ↓
2. Folder Structure
        ↓
3. Python domain models
        ↓
4. Experience ingestion
        ↓
5. Node + Association engine
        ↓
6. Activation mathematics
        ↓
7. Unit tests
        ↓
8. PostgreSQL persistence
        ↓
9. LLM interpretation
        ↓
10. Retrieval
        ↓
11. Correction system
        ↓
12. Pattern formation
        ↓
13. Reasoning
        ↓
14. FastAPI
        ↓
15. Next.js Brain UI
        ↓
16. Realtime visualization
```

**Rule:** jangan membangun fitur yang belum memiliki model data dan test yang jelas.

---

# 64. Immediate Milestone

Milestone pertama Digital Self V2 adalah:

```text
ONE EXPERIENCE
        ↓
FORMAL DATA
        ↓
NODES
        ↓
RELATIONSHIPS
        ↓
WEIGHTS
        ↓
ACTIVATION
        ↓
TRACEABLE MEMORY
```

Jika satu experience sudah dapat melalui pipeline tersebut secara deterministik dan dapat diuji, maka **otak pertama Digital Self sudah hidup secara computationally**.

Baru setelah itu kita beri kemampuan untuk berkembang.



------------------------------------------------------------------------------------------------------------------------------------------
# Digital Self — V2.1 Initial Technical Contract

## 1. Purpose

V2.1 menerjemahkan prinsip dan arsitektur pada PRD V2 menjadi kontrak teknis minimum sebelum implementasi Brain Engine dimulai.

Tahap ini tidak bertujuan membangun seluruh Digital Self. Fokusnya adalah memastikan struktur data dasar dapat menyimpan pengalaman, konsep, dan hubungan antar-konsep secara konsisten.

Prinsip utama:

> **Mulai dari data dan kontrak teknis sebelum membangun mekanisme pembelajaran yang kompleks.**

---

## 2. Initial Technical Scope

Implementasi awal hanya menggunakan tiga entitas utama:

1. `experiences`
2. `nodes`
3. `associations`

Belum diimplementasikan:

- `patterns`
- `beliefs`
- `decisions`
- `assemblies`
- `internal_states`
- reasoning engine
- consolidation engine

Entitas tersebut akan ditambahkan setelah fondasi memory graph terbukti berjalan dengan benar.

---

## 3. Initial Project Structure

Tahap awal menggunakan struktur minimal:

```text
digital-self/
├── schema.sql
├── models.py
├── params.yaml
└── tests/
```

### `schema.sql`

Menjadi kontrak struktur database.

Bertanggung jawab mendefinisikan:

- tabel
- kolom
- tipe data
- primary key
- foreign key
- constraint
- timestamp
- provenance

### `models.py`

Menjadi kontrak data pada application layer menggunakan Pydantic.

Model harus merepresentasikan domain yang sama dengan `schema.sql`.

### `params.yaml`

Menyimpan parameter pembelajaran dan aktivasi yang dapat dikonfigurasi tanpa mengubah source code.

---

## 4. Experience Contract

`experiences` merupakan sumber data paling dasar dalam Digital Self.

Minimal menyimpan:

```text
id
raw_text
occurred_at
created_at
metadata
```

### Rules

- `raw_text` harus dipertahankan.
- Raw experience tidak boleh ditimpa oleh hasil interpretasi.
- `occurred_at` menunjukkan kapan pengalaman terjadi.
- `created_at` menunjukkan kapan pengalaman dicatat ke sistem.
- Interpretasi AI tidak dianggap sebagai raw truth.
- Setiap hasil interpretasi harus dapat ditelusuri kembali ke experience sumbernya.

---

## 5. Node Contract

`nodes` merepresentasikan konsep atau entitas yang ditemukan dari pengalaman.

Minimal menyimpan:

```text
id
type
name
confidence
activation
first_seen
last_seen
```

Contoh node:

```text
Person
Place
Object
Event
Emotion
Action
Concept
```

Node tidak boleh langsung dianggap sebagai fakta permanen tentang pengguna.

Node merupakan representasi sistem terhadap informasi yang ditemukan dari pengalaman dan dapat mengalami perubahan, penggabungan, pemisahan, atau koreksi.

---

## 6. Association Contract

`associations` merepresentasikan hubungan antara dua node.

Minimal harus menyimpan:

```text
id
source_node
target_node
type
strength
confidence
source_experience
created_at
updated_at
```

Association harus memiliki provenance.

Sistem harus dapat menjawab:

> “Mengapa hubungan antara node A dan node B ada?”

Jawabannya harus dapat ditelusuri menuju satu atau lebih `experiences`.

Association juga tidak otomatis berarti hubungan sebab-akibat.

Contoh:

```text
Person → co_occurs_with → Office
```

tidak boleh otomatis diubah menjadi:

```text
Person → causes → Office
```

---

## 7. Initial Learning Parameters

Parameter awal disimpan di `params.yaml`.

Contoh:

```yaml
learning:
  alpha: 0.20
  beta: 0.10
  decay_lambda: 0.01

activation:
  threshold: 0.20
  max_depth: 3

pattern:
  minimum_evidence: 3
```

Nilai tersebut merupakan **initial parameters**, bukan nilai final.

Parameter harus dapat diubah tanpa memodifikasi source code.

Tujuannya agar perilaku learning dan activation dapat diuji serta dikalibrasi secara eksperimental.

---

## 8. Initial Learning Rules

Association strength menggunakan mekanisme sederhana pada tahap awal.

Positive evidence:

```text
s_new = s_old + α × w × (1 - s_old)
```

Negative evidence:

```text
s_new = s_old - β × w × s_old
```

Decay:

```text
s_new = s_old × exp(-λ × Δt)
```

Parameter:

- `s` = association strength
- `α` = positive learning rate
- `β` = negative learning rate
- `w` = evidence weight
- `λ` = decay rate
- `Δt` = elapsed time

Formula ini digunakan sebagai baseline dan dapat berubah berdasarkan hasil evaluasi.

---

## 9. Initial Activation Rules

Activation awal menggunakan kombinasi faktor:

```text
activation =
    semantic relevance
    + recency
    + frequency
    + emotional salience
    + context similarity
    + association strength
    + internal state
```

Pada implementasi pertama, tidak semua faktor harus langsung tersedia.

Sistem harus terlebih dahulu menyediakan mekanisme activation sederhana yang:

- memiliki batas nilai;
- memiliki threshold;
- dapat mengalami decay;
- dapat dipengaruhi context;
- dapat dikembangkan menjadi spreading activation.

---

## 10. Development Principle

Implementasi dilakukan secara bertahap.

Urutan awal:

```text
PRD V2
↓
schema.sql
↓
models.py
↓
params.yaml
↓
Database validation
↓
Experience ingestion
↓
Node creation
↓
Association creation
↓
Association learning
↓
Activation
↓
Testing
```

Tidak boleh langsung membangun seluruh Brain Engine sebelum kontrak data dasar tervalidasi.

---

## 11. Definition of Done — V2.1

V2.1 dianggap selesai apabila:

- `experiences` dapat menyimpan raw experience;
- `nodes` dapat merepresentasikan konsep dasar;
- `associations` dapat menghubungkan nodes;
- setiap association memiliki provenance;
- timestamp pengalaman dan timestamp pencatatan dapat dibedakan;
- Pydantic models sesuai dengan domain database;
- parameter learning tersimpan secara eksternal;
- data dapat ditulis dan dibaca kembali dengan konsisten;
- association strength dapat diperbarui menggunakan parameter awal;
- seluruh proses dasar dapat diuji tanpa membutuhkan pattern, belief, decision, atau reasoning engine.

---

## 12. Immediate Implementation Target

Setelah V2.1 disepakati, implementasi pertama hanya membuat tiga file:

```text
schema.sql
models.py
params.yaml
```

Setelah ketiga kontrak tersebut tervalidasi, barulah struktur Brain Engine dikembangkan.

**V2.1 tidak menambahkan kecerdasan baru.**

V2.1 hanya memastikan Digital Self memiliki fondasi data yang benar sebelum sistem mulai belajar dari pengalaman.