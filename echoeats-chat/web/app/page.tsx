'use client';

import { useState, useEffect, useRef } from 'react';
import { sendChat, sendVoiceChat, getChatHistory, speechToText, ChatResponse, VoiceChatResponse } from '../lib/api';

// TypeScript declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messageCount: number;
}

export default function Home() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [botTyping, setBotTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [isProcessingSpeech, setIsProcessingSpeech] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Load session ID from localStorage on component mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem('chatSessionId');
    if (savedSessionId) {
      setCurrentSessionId(savedSessionId);
      loadChatHistory(savedSessionId);
    }
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages, botTyping]);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const loadChatHistory = async (sessionId: string) => {
    try {
      const historyData = await getChatHistory(sessionId);
      const chatMessages: ChatMessage[] = historyData.history.map((msg, index) => ({
        role: msg.role,
        content: msg.content,
        timestamp: new Date(Date.now() - (historyData.history.length - index) * 60000)
      }));
      setMessages(chatMessages);
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  const generateSessionTitle = (firstMessage: string): string => {
    const words = firstMessage.split(' ').slice(0, 3);
    return words.join(' ').charAt(0).toUpperCase() + words.join(' ').slice(1);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      const audioChunks: BlobPart[] = [];
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        await processVoiceMessage(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processVoiceMessage = async (audioBlob: Blob) => {
    setIsProcessingSpeech(true);
    
    try {
      // First try ElevenLabs STT API
      const response = await speechToText(audioBlob);
      setIsProcessingSpeech(false);
      
      if (response.success && response.text.trim()) {
        await handleVoiceSubmit(response.text);
        return;
      }
    } catch (error) {
      console.log('ElevenLabs STT failed, trying Web Speech API:', error);
    }
    
    // Fallback to Web Speech API if ElevenLabs STT fails
    setIsProcessingSpeech(false);
    
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      
      recognition.onresult = async (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript.trim()) {
          await handleVoiceSubmit(transcript);
        }
      };
      
      recognition.onerror = (event) => {
        console.error('Web Speech API error:', event.error);
        setIsProcessingSpeech(false);
        
        // Handle different error types
        let errorMessage = "Speech recognition failed. What did you say?";
        
        switch (event.error) {
          case 'no-speech':
            errorMessage = "No speech detected. Please try speaking louder or closer to the microphone. What did you say?";
            setSpeechError("No speech detected. Try speaking louder.");
            break;
          case 'audio-capture':
            errorMessage = "Microphone access denied. Please allow microphone access and try again. What did you say?";
            setSpeechError("Microphone access denied.");
            break;
          case 'not-allowed':
            errorMessage = "Microphone permission denied. Please allow microphone access in your browser settings. What did you say?";
            setSpeechError("Microphone permission denied.");
            break;
          case 'network':
            errorMessage = "Network error occurred. Please check your internet connection. What did you say?";
            setSpeechError("Network error occurred.");
            break;
          default:
            errorMessage = `Speech recognition error: ${event.error}. What did you say?`;
            setSpeechError(`Speech error: ${event.error}`);
        }
        
        // Clear error after 3 seconds
        setTimeout(() => setSpeechError(null), 3000);
        
        // Final fallback to manual input
        const userMessage = prompt(errorMessage);
        if (userMessage) {
          handleVoiceSubmit(userMessage);
        }
      };
      
      recognition.start();
    } else {
      // Final fallback for browsers without speech recognition
      const userMessage = prompt("Speech recognition not supported. What did you say?");
      if (userMessage) {
        await handleVoiceSubmit(userMessage);
      }
    }
  };

  const playAudio = (audioBase64: string) => {
    if (!audioBase64) return;
    
    try {
      const audioBlob = new Blob([
        Uint8Array.from(atob(audioBase64), c => c.charCodeAt(0))
      ], { type: 'audio/mpeg' });
      
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      
      audio.onplay = () => setIsPlaying(true);
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.play();
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  };

  const handleVoiceSubmit = async (message: string) => {
    if (!message.trim()) return;

    const currentMessage = message;
    setMessage('');

    // Add user message to UI immediately
    const userMessage: ChatMessage = {
      role: 'user',
      content: currentMessage,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    // Show bot typing
    setBotTyping(true);

    try {
      const response: VoiceChatResponse = await sendVoiceChat(currentMessage, currentSessionId || undefined);
      
      // Update session ID if this is a new session
      if (!currentSessionId) {
        setCurrentSessionId(response.session_id);
        localStorage.setItem('chatSessionId', response.session_id);
        
        // Create new session
        const newSession: ChatSession = {
          id: response.session_id,
          title: generateSessionTitle(currentMessage),
          lastMessage: currentMessage,
          timestamp: new Date(),
          messageCount: response.message_count
        };
        setSessions(prev => [newSession, ...prev]);
      } else {
        // Update existing session
        setSessions(prev => prev.map(session => 
          session.id === currentSessionId 
            ? { ...session, lastMessage: currentMessage, messageCount: response.message_count }
            : session
        ));
      }
      
      // Simulate typing delay
      setTimeout(() => {
        setBotTyping(false);
        
        // Add assistant response to UI
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.reply,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        // Play audio response
        if (response.audio) {
          playAudio(response.audio);
        }
      }, Math.min(response.reply.length * 50, 2000));
      
    } catch (error) {
      console.error('Error:', error);
      setBotTyping(false);
      
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Error: Failed to send voice message',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const currentMessage = message;
    setMessage('');

    // Add user message to UI immediately
    const userMessage: ChatMessage = {
      role: 'user',
      content: currentMessage,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    // Show bot typing
    setBotTyping(true);

    try {
      const response: ChatResponse = await sendChat(currentMessage, currentSessionId || undefined);
      
      // Update session ID if this is a new session
      if (!currentSessionId) {
        setCurrentSessionId(response.session_id);
        localStorage.setItem('chatSessionId', response.session_id);
        
        // Create new session
        const newSession: ChatSession = {
          id: response.session_id,
          title: generateSessionTitle(currentMessage),
          lastMessage: currentMessage,
          timestamp: new Date(),
          messageCount: response.message_count
        };
        setSessions(prev => [newSession, ...prev]);
      } else {
        // Update existing session
        setSessions(prev => prev.map(session => 
          session.id === currentSessionId 
            ? { ...session, lastMessage: currentMessage, messageCount: response.message_count }
            : session
        ));
      }
      
      // Simulate typing delay
      setTimeout(() => {
        setBotTyping(false);
        
        // Add assistant response to UI
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.reply,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, assistantMessage]);
      }, Math.min(response.reply.length * 50, 2000)); // Typing delay based on response length
      
    } catch (error) {
      console.error('Error:', error);
      setBotTyping(false);
      
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Error: Failed to send message',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const startNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    localStorage.removeItem('chatSessionId');
  };

  const switchToSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    localStorage.setItem('chatSessionId', sessionId);
    loadChatHistory(sessionId);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Left Sidebar - Chat History */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-blue-600">
              Chat History ({sessions.length})
            </h2>
            <div className="flex space-x-2">
              <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
                </svg>
              </button>
              <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              <p className="text-sm">No chat history yet</p>
              <p className="text-xs mt-1">Start a conversation to see it here</p>
            </div>
          ) : (
            <div className="p-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => switchToSession(session.id)}
                  className={`p-4 rounded-lg cursor-pointer transition-all duration-200 hover:bg-blue-50 ${
                    currentSessionId === session.id ? 'bg-blue-50 border border-blue-200' : 'hover:shadow-sm'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {session.title}
                      </h3>
                      <p className="text-xs text-gray-500 mt-1" style={{
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden'
                      }}>
                        {session.lastMessage}
                      </p>
                    </div>
                    <div className="text-xs text-gray-400 ml-2">
                      {session.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* New Chat Button */}
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={startNewChat}
            className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors duration-200 font-medium"
          >
            + New Chat
          </button>
        </div>
      </div>

      {/* Right Side - Main Chat Area */}
      <div className="flex-1 flex flex-col h-screen">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">EchoEats Assistant</h1>
              {currentSessionId && (
                <p className="text-sm text-gray-500 mt-1">
                  Session: {currentSessionId.slice(0, 8)}...
                </p>
              )}
            </div>
            <button
              onClick={() => setVoiceMode(!voiceMode)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                voiceMode 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {voiceMode ? '🎤 Voice Mode' : '💬 Text Mode'}
            </button>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 p-2 sm:p-6 justify-between flex flex-col">
          <div className="flex flex-col space-y-4 p-3 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-700 rounded-full flex items-center justify-center mb-6">
                  <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-blue-600 mb-2">
                  Hello! How can I help you?
                </h2>
                <p className="text-gray-600 mb-8 max-w-md">
                  I'm your AI assistant ready to help with any questions you have.
                </p>
              </div>
            ) : (
              messages.map((msg, index) => (
                <div key={index}>
                  <div className={`flex items-end ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    <div className={`flex flex-col space-y-2 text-md leading-tight max-w-lg mx-2 ${
                      msg.role === 'user' ? 'order-1 items-end' : 'order-2 items-start'
                    }`}>
                      <div>
                        <span 
                          className={`px-4 py-3 rounded-xl inline-block ${
                            msg.role === 'user' 
                              ? 'rounded-br-none bg-blue-500 text-white' 
                              : 'rounded-bl-none bg-gray-100 text-gray-600'
                          }`}
                        >
                          {msg.content}
                        </span>
                      </div>
                    </div>
                    <img 
                      src={msg.role === 'user' ? 'https://i.pravatar.cc/100?img=7' : 'https://cdn.icon-icons.com/icons2/1371/PNG/512/robot02_90810.png'} 
                      alt="" 
                      className={`w-6 h-6 rounded-full ${
                        msg.role === 'user' ? 'order-2' : 'order-1'
                      }`} 
                    />
                  </div>
                </div>
              ))
            )}
            
            {/* Bot Typing Indicator */}
            {botTyping && (
              <div className="flex items-end">
                <div className="flex flex-col space-y-2 text-md leading-tight mx-2 order-2 items-start">
                  <div>
                    <img 
                      src="https://support.signal.org/hc/article_attachments/360016877511/typing-animation-3x.gif" 
                      alt="..." 
                      className="w-16 ml-6"
                    />
                  </div>
                </div>
                <img 
                  src="https://cdn.icon-icons.com/icons2/1371/PNG/512/robot02_90810.png" 
                  alt="" 
                  className="w-6 h-6 rounded-full order-1" 
                />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

        {/* Message Input */}
        <div className="border-t-2 border-gray-200 px-4 pt-4 mb-2 sm:mb-0">
          {voiceMode ? (
            /* Voice Input */
            <div className="flex items-center justify-center space-x-4">
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isProcessingSpeech}
                className={`px-6 py-3 rounded-full font-medium transition-all ${
                  isRecording 
                    ? 'bg-red-500 text-white animate-pulse' 
                    : isProcessingSpeech
                    ? 'bg-yellow-500 text-white cursor-not-allowed'
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                }`}
              >
                {isRecording 
                  ? '🛑 Stop Recording' 
                  : isProcessingSpeech 
                  ? '🔄 Processing Speech...' 
                  : '🎤 Start Recording'
                }
              </button>
              {isPlaying && (
                <div className="flex items-center text-blue-500">
                  <div className="animate-pulse">🔊 Playing response...</div>
                </div>
              )}
              {speechError && (
                <div className="flex items-center text-red-500">
                  <div className="text-sm">⚠️ {speechError}</div>
                </div>
              )}
            </div>
          ) : (
            /* Text Input */
            <div className="relative flex">
              <input 
                type="text" 
                placeholder="Say something..." 
                autoComplete="off" 
                autoFocus={true}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                className="text-md w-full focus:outline-none focus:placeholder-gray-400 text-gray-600 placeholder-gray-600 pl-5 pr-16 bg-gray-100 border-2 border-gray-200 focus:border-blue-500 rounded-full py-2" 
              />
              <div className="absolute right-2 items-center inset-y-0 hidden sm:flex">
                <button 
                  type="button" 
                  className="inline-flex items-center justify-center rounded-full h-8 w-8 transition duration-200 ease-in-out text-white bg-blue-500 hover:bg-blue-600 focus:outline-none" 
                  onClick={(e) => {
                    e.preventDefault();
                    handleSubmit(e);
                  }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          )}
        </div>
        </div>
      </div>
    </div>
  );
}