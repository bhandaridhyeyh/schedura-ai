# 🤖 Schedura AI

An intelligent booking assistant built with **FastAPI** (backend) and **Vite + React** (frontend).  
It helps users chat naturally with an AI to schedule appointments, confirm bookings, and manage availability.

---

## ✨ Features
- 💬 **Conversational AI** – Natural chat interface powered by structured responses.  
- 📅 **Smart Scheduling** – Users can pick dates & times with a modern DateTime selector.  
- ⚡ **Real-time Updates** – Instant responses with typing indicators for a smooth experience.  
- 🔗 **API-driven** – Built on REST APIs using FastAPI.  
- 🎨 **Modern UI** – Clean React design with interactive chat bubbles.
- ✅ **Booking Confirmation** – Creates bookings and sends an e-mail after confirmation.  

---

## 🚀 Getting Started

### 1. Clone Repository
```bash
git clone https://github.com/bhandaridhyeyh/schedura-ai.git
cd schedura-ai
````

### 2. Backend Setup

```bash
cd Backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Runs at: `http://127.0.0.1:8000`

### 3. Frontend Setup

```bash
cd Frontend
npm install
npm run dev
```

Runs at: `http://localhost:5173`

---

## 📡 API Endpoints

* `POST /chat` – Send user messages, get AI response

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request