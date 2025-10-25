import os
import uuid
import json
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from order_tool import ORDER_TOOLS

# Load environment variables
load_dotenv()

class SimpleMemory:
    """Simple in-memory storage for chat history."""
    
    def __init__(self):
        self._sessions: Dict[str, List] = {}
    
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
        self.model_with_tools = None
        self.memory = SimpleMemory()
        
        if self.api_key and self.api_base and self.model_name:
            try:
                self.model = ChatOpenAI(
                    model=self.model_name,
                    base_url=self.api_base,
                    api_key=self.api_key,
                    temperature=0.7
                )
                # Bind tools to the model
                self.model_with_tools = self.model.bind_tools(ORDER_TOOLS)
                print(f"Successfully initialized LangChain with model: {self.model_name}")
                print(f"Bound {len(ORDER_TOOLS)} tools to the model")
            except Exception as e:
                print(f"Failed to initialize LangChain: {e}")
                self.model = None
                self.model_with_tools = None

    async def chat_once(self, message: str, session_id: Optional[str] = None) -> Dict:
        """Send a message to the LLM and return the response with session info."""
        if not self.model_with_tools:
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
            
            # Create conversation messages
            messages = [
                SystemMessage(content="You are a helpful assistant for EchoEats restaurant. Be friendly and engaging in your responses. You have access to order search tools to help customers find their previous orders. Use these tools when customers ask about their order history.")
            ]
            
            # Add conversation history
            messages.extend(existing_messages)
            
            # Add current user message
            messages.append(HumanMessage(content=message))
            
            # Get response from model with tools
            response = self.model_with_tools.invoke(messages)
            
            # Check if the model wants to call tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute tool calls
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    # Find and execute the tool
                    for tool in ORDER_TOOLS:
                        if tool.name == tool_name:
                            try:
                                result = tool.invoke(tool_args)
                                tool_results.append(f"Tool {tool_name}: {result}")
                            except Exception as e:
                                tool_results.append(f"Tool {tool_name} error: {str(e)}")
                            break
                
                # Create a new message with tool results
                tool_message = AIMessage(content=f"Tool results: {'; '.join(tool_results)}")
                messages.append(tool_message)
                
                # Get final response
                final_response = self.model_with_tools.invoke(messages)
                final_content = final_response.content
            else:
                final_content = response.content
            
            # Save to memory
            self.memory.save_context(
                {"message": message, "session_id": session_id},
                {"reply": final_content}
            )
            
            # Get updated message count
            updated_memory = self.memory.load_memory_variables({"session_id": session_id})
            message_count = len(updated_memory["messages"])
            
            return {
                "reply": final_content,
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
