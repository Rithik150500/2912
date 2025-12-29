# AI Advocate Conversational Chatbot - Implementation Plan

## Overview

Transform the existing Telegram-based legal assistant into a full-featured **web application** with:
- AI-powered client interviewing, counselling, case analysis, and document drafting
- Intelligent advocate matching based on case profiles
- Dual portal system (Client & Advocate interfaces)
- Seamless handoff from AI to human advocate

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                            │
├─────────────────────────────┬───────────────────────────────────────┤
│      Client Portal          │         Advocate Portal               │
│  - AI Chat Interface        │  - Profile Management                 │
│  - Recommended Advocates    │  - Case Requests (Accept/Reject)      │
│  - Advocate Selection       │  - Accepted Cases Dashboard           │
│  - Live Chat with Advocate  │  - Continue Client Conversations      │
└─────────────────────────────┴───────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI/Python)                         │
│  - Authentication (JWT)                                             │
│  - WebSocket Server (Real-time chat)                                │
│  - Claude AI Integration                                            │
│  - Advocate Matching Engine                                         │
│  - REST APIs                                                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Database (PostgreSQL)                            │
│  - Users (clients, advocates)                                       │
│  - Conversations                                                    │
│  - Messages                                                         │
│  - Cases                                                            │
│  - Advocate Profiles                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### 1. Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('client', 'advocate') NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 2. Advocate Profiles Table
```sql
CREATE TABLE advocate_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    enrollment_number VARCHAR(50) UNIQUE NOT NULL,
    enrollment_year INTEGER,
    bar_council VARCHAR(100),
    states TEXT[],                    -- Array of states
    districts TEXT[],                 -- Array of districts
    home_court VARCHAR(100),
    primary_specializations TEXT[],   -- e.g., ['civil', 'matrimonial']
    sub_specializations TEXT[],       -- e.g., ['divorce', 'property_disputes']
    experience_years INTEGER,
    landmark_cases TEXT,
    success_rate DECIMAL(5,2),
    current_case_load INTEGER DEFAULT 0,
    max_case_capacity INTEGER DEFAULT 20,
    fee_category ENUM('premium', 'standard', 'affordable', 'pro_bono'),
    consultation_fee DECIMAL(10,2),
    languages TEXT[],                 -- e.g., ['hindi', 'english', 'marathi']
    office_address TEXT,
    rating DECIMAL(3,2) DEFAULT 0.0,
    review_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Cases Table
```sql
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES users(id),
    advocate_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),

    -- Case Profile (extracted from AI conversation)
    matter_type VARCHAR(50),          -- civil, matrimonial, criminal, etc.
    sub_category VARCHAR(100),
    state VARCHAR(100),
    district VARCHAR(100),
    court_level VARCHAR(50),          -- district, high_court, supreme_court
    complexity VARCHAR(20),           -- simple, moderate, complex
    urgency VARCHAR(20),              -- urgent, normal, can_wait
    amount_in_dispute DECIMAL(15,2),
    case_summary TEXT,
    extracted_facts JSONB,

    -- Status Management
    status ENUM('ai_conversation', 'pending_advocate', 'advocate_assigned',
                'advocate_rejected', 'in_progress', 'completed', 'closed')
           DEFAULT 'ai_conversation',

    -- Advocate Selection
    selected_advocate_id UUID REFERENCES users(id),
    advocate_response ENUM('pending', 'accepted', 'rejected'),
    rejection_reason TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Conversations Table
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    client_id UUID REFERENCES users(id) NOT NULL,

    -- Conversation phases
    phase ENUM('ai_interview', 'ai_counselling', 'ai_drafting',
               'advocate_review', 'advocate_active') DEFAULT 'ai_interview',

    -- AI state
    ai_container_id VARCHAR(255),     -- Claude container for context

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Messages Table
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,

    sender_type ENUM('client', 'ai', 'advocate') NOT NULL,
    sender_id UUID,                   -- NULL for AI messages

    content TEXT NOT NULL,
    message_type ENUM('text', 'file', 'document', 'system') DEFAULT 'text',
    file_url VARCHAR(500),
    file_name VARCHAR(255),

    -- For advocate visibility
    visible_to_advocate BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6. Advocate Case Requests Table
```sql
CREATE TABLE advocate_case_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    advocate_id UUID REFERENCES users(id),
    client_id UUID REFERENCES users(id),

    match_score INTEGER,              -- 0-100
    match_explanation TEXT,

    status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
    response_at TIMESTAMP,
    rejection_reason TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7. Notifications Table
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    type VARCHAR(50),                 -- 'case_request', 'advocate_accepted', 'advocate_rejected', etc.
    title VARCHAR(255),
    message TEXT,
    data JSONB,                       -- Additional context
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Endpoints

### Authentication APIs
```
POST   /api/auth/register          - Register new user (client/advocate)
POST   /api/auth/login             - Login and get JWT
POST   /api/auth/refresh           - Refresh JWT token
POST   /api/auth/logout            - Logout
GET    /api/auth/me                - Get current user profile
```

### Client APIs
```
POST   /api/client/conversations              - Start new AI conversation
GET    /api/client/conversations              - List all conversations
GET    /api/client/conversations/:id          - Get conversation details
POST   /api/client/conversations/:id/messages - Send message to AI
GET    /api/client/conversations/:id/messages - Get conversation history

GET    /api/client/cases                      - List client's cases
GET    /api/client/cases/:id                  - Get case details
POST   /api/client/cases/:id/select-advocate  - Select an advocate
GET    /api/client/cases/:id/recommendations  - Get recommended advocates

GET    /api/client/notifications              - Get notifications
```

### Advocate APIs
```
GET    /api/advocate/profile                  - Get own profile
PUT    /api/advocate/profile                  - Update profile
PUT    /api/advocate/availability             - Toggle availability

GET    /api/advocate/case-requests            - List pending case requests
GET    /api/advocate/case-requests/:id        - Get case request with full conversation
POST   /api/advocate/case-requests/:id/accept - Accept a case
POST   /api/advocate/case-requests/:id/reject - Reject a case (with reason)

GET    /api/advocate/cases                    - List accepted cases
GET    /api/advocate/cases/:id                - Get case with conversation history
POST   /api/advocate/cases/:id/messages       - Send message to client

GET    /api/advocate/notifications            - Get notifications
```

### WebSocket Endpoints
```
WS     /ws/chat/:conversation_id              - Real-time chat connection
```

---

## Implementation Steps

### Phase 1: Database & Backend Foundation
1. Set up PostgreSQL database with schema
2. Create FastAPI project structure
3. Implement SQLAlchemy models
4. Set up Alembic for migrations
5. Implement JWT authentication
6. Create base CRUD operations

### Phase 2: AI Conversation System
1. Port Claude integration from existing bot
2. Implement conversation service
3. Create message handling with history
4. Implement case profile extraction
5. Add document generation capability

### Phase 3: Advocate Matching Engine
1. Port matching algorithm from existing code
2. Create recommendation service
3. Implement case request workflow
4. Add accept/reject functionality

### Phase 4: Real-time Communication
1. Set up WebSocket infrastructure
2. Implement real-time message delivery
3. Create notification system
4. Handle AI-to-Advocate handoff

### Phase 5: Frontend - Client Portal
1. Set up React project with TypeScript
2. Create authentication pages
3. Build AI chat interface
4. Implement advocate recommendation view
5. Add advocate selection workflow
6. Build live chat with advocate

### Phase 6: Frontend - Advocate Portal
1. Create advocate dashboard
2. Build profile management page
3. Implement case requests view with conversation history
4. Add accept/reject functionality
5. Build accepted cases dashboard
6. Create client chat continuation interface

### Phase 7: Integration & Polish
1. End-to-end testing
2. Error handling improvements
3. UI/UX polish
4. Performance optimization

---

## Key User Flows

### Flow 1: Client AI Conversation → Advocate Recommendation

```
1. Client registers/logs in
2. Client starts new conversation
3. AI conducts interview (fact-gathering)
4. AI provides counselling and case analysis
5. AI offers document drafting
6. System extracts case profile
7. System runs matching algorithm
8. Client sees recommended advocates (ranked by match score)
```

### Flow 2: Client Selects Advocate

```
1. Client views recommended advocates
2. Client selects preferred advocate
3. System creates case request for advocate
4. Advocate receives notification
5. Case status: "pending_advocate"
```

### Flow 3: Advocate Reviews & Accepts Case

```
1. Advocate logs into portal
2. Advocate sees pending case requests
3. Advocate clicks to view full AI conversation history
4. Advocate reviews case profile & client facts
5. Advocate clicks "Accept"
6. Client notified: "Advocate accepted your case"
7. AI conversation transitions to Advocate conversation
```

### Flow 4: Advocate Rejects → Client Chooses Another

```
1. Advocate reviews case request
2. Advocate clicks "Reject" (with optional reason)
3. Client notified: "Advocate declined. Please select another."
4. Client returns to recommendations
5. Previously rejected advocate marked as unavailable for this case
6. Client selects different advocate
```

### Flow 5: Advocate Continues Conversation

```
1. Advocate opens accepted case
2. Advocate sees full conversation history (Client ↔ AI)
3. Advocate sends message (replaces AI)
4. Client receives message from advocate (not AI)
5. Real-time chat continues between Client ↔ Advocate
```

---

## File Structure

```
/home/user/2912/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Configuration
│   │   ├── database.py             # Database connection
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── advocate_profile.py
│   │   │   ├── case.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   └── notification.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── case.py
│   │   │   ├── conversation.py
│   │   │   └── advocate.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── client.py
│   │   │   ├── advocate.py
│   │   │   └── websocket.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── ai_service.py       # Claude integration
│   │   │   ├── matching_service.py # Advocate matching
│   │   │   ├── conversation_service.py
│   │   │   ├── case_service.py
│   │   │   └── notification_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── security.py         # JWT, password hashing
│   │       └── websocket_manager.py
│   ├── alembic/                    # Database migrations
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── ChatInput.tsx
│   │   │   ├── advocates/
│   │   │   │   ├── AdvocateCard.tsx
│   │   │   │   ├── AdvocateList.tsx
│   │   │   │   └── AdvocateProfile.tsx
│   │   │   ├── cases/
│   │   │   │   ├── CaseCard.tsx
│   │   │   │   ├── CaseRequestCard.tsx
│   │   │   │   └── ConversationHistory.tsx
│   │   │   └── common/
│   │   │       ├── Navbar.tsx
│   │   │       ├── Sidebar.tsx
│   │   │       └── Notification.tsx
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   │   ├── Login.tsx
│   │   │   │   └── Register.tsx
│   │   │   ├── client/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Conversation.tsx
│   │   │   │   ├── SelectAdvocate.tsx
│   │   │   │   └── Cases.tsx
│   │   │   └── advocate/
│   │   │       ├── Dashboard.tsx
│   │   │       ├── Profile.tsx
│   │   │       ├── CaseRequests.tsx
│   │   │       ├── CaseRequestDetail.tsx
│   │   │       ├── AcceptedCases.tsx
│   │   │       └── CaseChat.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── authService.ts
│   │   │   └── websocketService.ts
│   │   ├── store/
│   │   │   ├── authStore.ts
│   │   │   ├── chatStore.ts
│   │   │   └── notificationStore.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── advocate_bot_complete.py        # Existing Telegram bot (reference)
└── PLAN.md                         # This file
```

---

## Technology Choices

| Component | Technology | Reason |
|-----------|------------|--------|
| Backend Framework | FastAPI | Async support, WebSocket native, Python (reuse existing code) |
| Database | PostgreSQL | Robust, JSONB support, production-ready |
| ORM | SQLAlchemy 2.0 | Async support, Python standard |
| Migrations | Alembic | SQLAlchemy integration |
| Auth | JWT (PyJWT) | Stateless, scalable |
| AI | Anthropic Claude API | Already integrated in existing code |
| Frontend | React + TypeScript | Modern, type-safe |
| State Management | Zustand | Lightweight, simple |
| Styling | Tailwind CSS | Rapid development |
| Real-time | WebSockets (native) | Built into FastAPI |
| Build Tool | Vite | Fast development |

---

## Questions for Clarification

1. **Advocate Registration**: Should advocates self-register or be admin-verified before appearing in recommendations?

2. **Multiple Advocate Selection**: Can a client select multiple advocates simultaneously, or must they wait for rejection before selecting another?

3. **Document Storage**: Should generated legal documents be stored persistently or just delivered once?

4. **Payment Integration**: Is there a payment flow for advocate consultations?

5. **Mobile App**: Is mobile responsiveness sufficient, or is a native app required later?

6. **Existing Bot**: Should the Telegram bot continue to work alongside the web app?

---

## Summary

This plan transforms the existing Telegram bot into a full-featured web application with:

- **Client Portal**: AI conversation → Case analysis → Advocate recommendations → Selection → Live chat
- **Advocate Portal**: Profile management → Case requests (with full history) → Accept/Reject → Continue conversation
- **Seamless Handoff**: AI-to-human advocate transition with complete context preservation
- **Real-time Communication**: WebSocket-based live chat after advocate acceptance

The implementation preserves the existing Claude AI integration and matching algorithm while adding persistent storage, authentication, and a modern web interface.
