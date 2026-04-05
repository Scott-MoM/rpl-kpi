from supabase import Client, create_client

from ..core.config import settings


def get_supabase_client() -> Client | None:
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


def get_supabase_admin_client() -> Client | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_server_client() -> Client | None:
    return get_supabase_admin_client() or get_supabase_client()
