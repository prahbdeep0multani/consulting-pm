from .clients import router as clients_router
from .projects import router as projects_router
from .tasks import router as tasks_router
from .attachments import router as attachments_router

__all__ = ["clients_router", "projects_router", "tasks_router", "attachments_router"]
