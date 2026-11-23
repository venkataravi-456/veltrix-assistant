from typing import Dict, Any, Optional

class Session:
    def __init__(self, session_id: str, employee_id: str):
        self.session_id = session_id
        self.employee_id = employee_id
        self.pending_proposal: Optional[Dict[str, Any]] = None
        self.history: list = []

class SessionStore:
    def __init__(self):
        # Maps session_id -> Session
        self.sessions: Dict[str, Session] = {}

    def get_or_create(self, session_id: str, employee_id: str) -> Optional[Session]:
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Verify session ownership (Section 7.1)
            if session.employee_id != employee_id:
                return None  # Will trigger 403
            return session
        
        session = Session(session_id, employee_id)
        self.sessions[session_id] = session
        return session

    def set_pending_proposal(self, session_id: str, proposal: Dict[str, Any]):
        if session_id in self.sessions:
            self.sessions[session_id].pending_proposal = proposal

    def clear_pending_proposal(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id].pending_proposal = None

session_store = SessionStore()
