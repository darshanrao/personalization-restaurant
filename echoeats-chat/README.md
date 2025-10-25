# EchoEats Chat - Minimal Full-Stack Chatbot Starter

A minimal full-stack chatbot connection starter with FastAPI backend and Next.js frontend.

## Project Structure

```
/echoeats-chat
  /server          # FastAPI backend
  /web            # Next.js frontend
```

## Backend Setup (FastAPI)

1. Navigate to the server directory:
   ```bash
   cd echoeats-chat/server
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment file and configure:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your NVIDIA API credentials if available.

5. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

The backend will be available at `http://localhost:8000`

## Frontend Setup (Next.js)

1. Navigate to the web directory:
   ```bash
   cd echoeats-chat/web
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy the environment file:
   ```bash
   cp .env.local.example .env.local
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`

## Usage

1. Start both the backend and frontend servers
2. Open `http://localhost:3000` in your browser
3. Type a message and click "Send"
4. The backend will respond with either:
   - A response from NVIDIA Nemotron (if API keys are configured)
   - An echo of your message (if API keys are not configured)

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /chat` - Chat endpoint that accepts `{message: string}` and returns `{reply: string}`

## Features

- ✅ FastAPI backend with CORS enabled
- ✅ Next.js 14 with TypeScript and App Router
- ✅ LangChain integration with NVIDIA Nemotron
- ✅ Fallback echo functionality when API keys are not configured
- ✅ Minimal chat UI with Tailwind CSS
- ✅ Health check proxy endpoint
- ✅ Environment-based configuration
