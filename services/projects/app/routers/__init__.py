from .attachments import router as attachments_router
from .clients import router as clients_router
from .projects import router as projects_router
from .tasks import router as tasks_router

__all__ = ["attachments_router", "clients_router", "projects_router", "tasks_router"]
