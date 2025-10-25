# EchoEats Chat - Docker Setup Instructions

## ✅ Docker Setup Status: READY!

The Docker setup has been tested and verified. Here's what was fixed:

### 🔧 Issues Fixed:
1. **Added `curl` to both Dockerfiles** for health checks
2. **Fixed frontend dependencies** - now installs dev dependencies for build
3. **Simplified environment variables** - uses `.env` file instead of individual env vars
4. **Added proper service dependencies** - frontend waits for backend health check
5. **Removed obsolete Docker Compose version** - no more warnings

### 🚀 Ready to Use Commands:

```bash
# 1. Create your .env file (copy from .env.example)
cp .env.example .env
# Edit .env with your actual API keys

# 2. Build and run everything
docker-compose up --build

# 3. Access the app
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

## Prerequisites for Windows

1. **Install Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Make sure to enable WSL 2 backend if prompted
   - Restart your computer after installation

2. **Install Git for Windows** (if not already installed)
   - Download from: https://git-scm.com/download/win

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd personalization-restaurant/echoeats-chat
```

### 2. Create Environment File
Create a `.env` file in the **root directory** (same level as `docker-compose.yml`) with your API keys:

```bash
# NVIDIA API Configuration
NIM_API_KEY=your_nvidia_api_key_here
NIM_API_BASE=https://integrate.api.nvidia.com/v1
MODEL_NAME=nvidia/nemotron-mini-4b-instruct

# ElevenLabs API Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb

# CORS Configuration
ALLOW_ORIGIN=http://localhost:3000
```

### 3. Build and Run with Docker Compose
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up --build -d
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health

## Available Commands

### Start Services
```bash
docker-compose up
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend
```

### Rebuild Services
```bash
docker-compose up --build
```

### Remove Everything (including volumes)
```bash
docker-compose down -v
```

## Troubleshooting

### Port Already in Use
If ports 3000 or 8000 are already in use:
```bash
# Kill processes using these ports
netstat -ano | findstr :3000
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

### Docker Desktop Issues
- Make sure Docker Desktop is running
- Check if WSL 2 is enabled
- Restart Docker Desktop if needed

### Environment Variables
- Make sure your `.env` file is in the root directory
- Check that all API keys are valid
- Restart containers after changing environment variables:
  ```bash
  docker-compose down
  docker-compose up --build
  ```

## Features Available

✅ **Intelligent Order Search**: Ask questions like "What did I order last Friday?"
✅ **Voice-to-Voice Chat**: Complete speech-to-text and text-to-speech
✅ **Session Memory**: Maintains conversation context
✅ **RESTful API**: Full backend API with health checks
✅ **Modern UI**: Responsive Next.js frontend

## API Endpoints

- `GET /health` - Health check
- `POST /chat` - Text chat with memory
- `POST /voice/chat` - Voice chat with TTS
- `POST /voice/stt` - Speech-to-text conversion
- `GET /chat/history/{session_id}` - Get chat history

## Need Help?

If you encounter any issues:
1. Check the logs: `docker-compose logs`
2. Verify your API keys are correct
3. Make sure Docker Desktop is running
4. Try rebuilding: `docker-compose up --build`
