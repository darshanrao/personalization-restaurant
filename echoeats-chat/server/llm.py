import os
import uuid
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.memory import BaseMemory

# Load environment variables
load_dotenv()

class SimpleMemory(BaseMemory):
    """Simple in-memory storage for chat history."""
    
    def __init__(self):
        super().__init__()
        self._sessions: Dict[str, List] = {}
    
    @property
    def memory_variables(self) -> List[str]:
        return ["messages"]
    
    def load_memory_variables(self, inputs: Dict[str, any]) -> Dict[str, any]:
        session_id = inputs.get("session_id", "default")
        messages = self._sessions.get(session_id, [])
        return {"messages": messages}
    
    def save_context(self, inputs: Dict[str, any], outputs: Dict[str, str]) -> None:
        session_id = inputs.get("session_id", "default")
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        # Add user message
        if "message" in inputs:
            self._sessions[session_id].append(HumanMessage(content=inputs["message"]))
        
        # Add AI response
        if "reply" in outputs:
            self._sessions[session_id].append(AIMessage(content=outputs["reply"]))
    
    def clear(self) -> None:
        self._sessions.clear()

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("NIM_API_KEY")
        self.api_base = os.getenv("NIM_API_BASE")
        self.model_name = os.getenv("MODEL_NAME")
        
        # Initialize ChatOpenAI if credentials are available
        self.model = None
        self.memory = SimpleMemory()
        
        if self.api_key and self.api_base and self.model_name:
            try:
                self.model = ChatOpenAI(
                    model=self.model_name,
                    base_url=self.api_base,
                    api_key=self.api_key,
                    temperature=0.7
                )
                print(f"Successfully initialized LangChain with model: {self.model_name}")
            except Exception as e:
                print(f"Failed to initialize LangChain: {e}")
                self.model = None

    async def chat_once(self, message: str, session_id: Optional[str] = None) -> Dict:
        """Send a message to the LLM and return the response with session info."""
        if not self.model:
            return {
                "reply": f"echo: {message}",
                "session_id": session_id or str(uuid.uuid4()),
                "message_count": 0
            }
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Get existing messages for this session
            memory_vars = self.memory.load_memory_variables({"session_id": session_id})
            existing_messages = memory_vars["messages"]
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Be friendly and engaging in your responses."),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])
            
            # Create chain
            chain = prompt | self.model
            
            # Invoke the chain
            response = chain.invoke({
                "chat_history": existing_messages,
                "input": message
            })
            
            # Save to memory
            self.memory.save_context(
                {"message": message, "session_id": session_id},
                {"reply": response.content}
            )
            
            # Get updated message count
            updated_memory = self.memory.load_memory_variables({"session_id": session_id})
            message_count = len(updated_memory["messages"])
            
            return {
                "reply": response.content,
                "session_id": session_id,
                "message_count": message_count
            }
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return {
                "reply": f"echo: {message}",
                "session_id": session_id,
                "message_count": 0
            }

    def get_chat_history(self, session_id: str) -> List[Dict]:
        """Get chat history for a specific session."""
        try:
            memory_vars = self.memory.load_memory_variables({"session_id": session_id})
            messages = memory_vars["messages"]
            history = []
            
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    history.append({"role": "assistant", "content": msg.content})
            
            return history
            
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []

# Create a global instance
llm_service = LLMService()
