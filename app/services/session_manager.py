from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import threading
import time
from dataclasses import dataclass
from enum import Enum

class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class Message:
    """Represents a single message in the conversation"""
    content: str
    message_type: MessageType
    timestamp: datetime
    image_base64: Optional[str] = None
    
    def to_openai_format(self) -> Dict:
        """Convert message to OpenAI API format"""
        if self.message_type == MessageType.USER:
            if self.image_base64:
                return {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.content},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{self.image_base64}"}
                        }
                    ]
                }
            else:
                return {"role": "user", "content": self.content}
        elif self.message_type == MessageType.ASSISTANT:
            return {"role": "assistant", "content": self.content}
        else:  # SYSTEM
            return {"role": "system", "content": self.content}

class ConversationSession:
    """Manages a single user's conversation session"""
    
    def __init__(self, user_id: str, max_messages: int = 30, session_timeout: int = 3600):
        self.user_id = user_id
        self.messages: List[Message] = []
        self.max_messages = max_messages
        self.session_timeout = session_timeout  # in seconds (1 hour = 3600)
        self.last_activity = datetime.now()
        self.created_at = datetime.now()
        self._lock = threading.Lock()
    
    def add_message(self, content: str, message_type: MessageType, image_base64: Optional[str] = None):
        """Add a message to the conversation"""
        with self._lock:
            message = Message(
                content=content,
                message_type=message_type,
                timestamp=datetime.now(),
                image_base64=image_base64
            )
            
            self.messages.append(message)
            self.last_activity = datetime.now()
            
            # Implement FIFO: Remove oldest messages if limit exceeded
            if len(self.messages) > self.max_messages:
                # Keep system message if it's the first one
                if self.messages[0].message_type == MessageType.SYSTEM:
                    # Remove the second oldest message instead
                    self.messages.pop(1)
                else:
                    # Remove the oldest message
                    self.messages.pop(0)
    
    def get_messages_for_ai(self) -> List[Dict]:
        """Get messages in OpenAI API format"""
        with self._lock:
            return [msg.to_openai_format() for msg in self.messages]
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.now() - self.last_activity > timedelta(seconds=self.session_timeout)
    
    def get_session_info(self) -> Dict:
        """Get session information"""
        with self._lock:
            return {
                "user_id": self.user_id,
                "message_count": len(self.messages),
                "created_at": self.created_at.isoformat(),
                "last_activity": self.last_activity.isoformat(),
                "is_expired": self.is_expired(),
                "time_remaining": max(0, self.session_timeout - (datetime.now() - self.last_activity).total_seconds())
            }

class SessionManager:
    """Manages all user sessions with automatic cleanup"""
    
    def __init__(self, max_messages_per_session: int = 30, session_timeout: int = 3600, cleanup_interval: int = 300):
        self.sessions: Dict[str, ConversationSession] = {}
        self.max_messages_per_session = max_messages_per_session
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval  # cleanup every 5 minutes
        self._lock = threading.Lock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()
        
        print(f"[SESSION_MANAGER] Started with {max_messages_per_session} max messages, {session_timeout/60:.1f}min timeout")
    
    def get_or_create_session(self, user_id: str) -> ConversationSession:
        """Get existing session or create new one"""
        with self._lock:
            # Check if session exists and is not expired
            if user_id in self.sessions:
                session = self.sessions[user_id]
                if not session.is_expired():
                    return session
                else:
                    # Session expired, remove it
                    del self.sessions[user_id]
                    print(f"[SESSION_MANAGER] Expired session removed for user: {user_id}")
            
            # Create new session
            session = ConversationSession(
                user_id=user_id,
                max_messages=self.max_messages_per_session,
                session_timeout=self.session_timeout
            )
            self.sessions[user_id] = session
            print(f"[SESSION_MANAGER] New session created for user: {user_id}")
            return session
    
    def add_message(self, user_id: str, content: str, message_type: MessageType, image_base64: Optional[str] = None):
        """Add message to user's session"""
        session = self.get_or_create_session(user_id)
        session.add_message(content, message_type, image_base64)
        print(f"[SESSION_MANAGER] Message added for {user_id}: {message_type.value} ({len(session.messages)} total)")
    
    def get_conversation_context(self, user_id: str, system_prompt: str) -> List[Dict]:
        """Get full conversation context for AI, including system prompt"""
        session = self.get_or_create_session(user_id)
        messages = session.get_messages_for_ai()
        
        # Always ensure system message is first
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        return messages
    
    def get_session_info(self, user_id: str) -> Optional[Dict]:
        """Get session information for a user"""
        with self._lock:
            if user_id in self.sessions:
                return self.sessions[user_id].get_session_info()
            return None
    
    def clear_session(self, user_id: str) -> bool:
        """Manually clear a user's session"""
        with self._lock:
            if user_id in self.sessions:
                del self.sessions[user_id]
                print(f"[SESSION_MANAGER] Session manually cleared for user: {user_id}")
                return True
            return False
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        with self._lock:
            return len(self.sessions)
    
    def get_all_sessions_info(self) -> Dict:
        """Get information about all active sessions"""
        with self._lock:
            return {
                "active_sessions": len(self.sessions),
                "sessions": {
                    user_id: session.get_session_info() 
                    for user_id, session in self.sessions.items()
                }
            }
    
    def _cleanup_expired_sessions(self):
        """Background thread to cleanup expired sessions"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                expired_users = []
                
                with self._lock:
                    for user_id, session in self.sessions.items():
                        if session.is_expired():
                            expired_users.append(user_id)
                
                # Remove expired sessions
                for user_id in expired_users:
                    with self._lock:
                        if user_id in self.sessions:
                            del self.sessions[user_id]
                            print(f"[SESSION_MANAGER] Expired session cleaned up for user: {user_id}")
                
                if expired_users:
                    print(f"[SESSION_MANAGER] Cleaned up {len(expired_users)} expired sessions")
                    
            except Exception as e:
                print(f"[SESSION_MANAGER] Cleanup error: {e}")

# Global session manager instance
session_manager = SessionManager(
    max_messages_per_session=30,
    session_timeout=3600,  # 1 hour
    cleanup_interval=300   # cleanup every 5 minutes
)

# Utility functions for easy integration
def add_user_message(user_id: str, content: str, image_base64: Optional[str] = None):
    """Add user message to session"""
    session_manager.add_message(user_id, content, MessageType.USER, image_base64)

def add_assistant_message(user_id: str, content: str):
    """Add assistant message to session"""
    session_manager.add_message(user_id, content, MessageType.ASSISTANT)

def get_conversation_history(user_id: str, system_prompt: str) -> List[Dict]:
    """Get conversation history for AI model"""
    return session_manager.get_conversation_context(user_id, system_prompt)

def clear_user_session(user_id: str) -> bool:
    """Clear user's session"""
    return session_manager.clear_session(user_id)

def get_session_status(user_id: str) -> Optional[Dict]:
    """Get user's session status"""
    return session_manager.get_session_info(user_id)

# Example usage and testing functions
if __name__ == "__main__":
    # Test the session manager
    print("Testing Session Manager...")
    
    # Add some test messages
    add_user_message("user1", "Hello, I have a problem with my tomatoes")
    add_assistant_message("user1", "Hello! I can help you with tomato problems. What seems to be the issue?")
    add_user_message("user1", "The leaves are turning yellow")
    
    # Get conversation history
    system_prompt = "You are an agricultural expert assistant."
    history = get_conversation_history("user1", system_prompt)
    
    print(f"Conversation history for user1: {len(history)} messages")
    for msg in history:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    # Check session status
    status = get_session_status("user1")
    print(f"Session status: {status}")
    
    print("Session Manager test completed!")