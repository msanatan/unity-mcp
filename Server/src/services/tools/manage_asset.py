"""
Defines the manage_asset tool for interacting with Unity assets.
"""
import asyncio
import json
from typing import Annotated, Any, Literal

from fastmcp import Context
from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


@mcp_for_unity_tool(
    description="Performs asset operations (import, create, modify, delete, etc.) in Unity."
)
async def manage_asset(
    ctx: Context,
    action: Annotated[Literal["import", "create", "modify", "delete", "duplicate", "move", "rename", "search", "get_info", "create_folder", "get_components"], "Perform CRUD operations on assets."],
    path: Annotated[str, "Asset path (e.g., 'Materials/MyMaterial.mat') or search scope."],
    asset_type: Annotated[str,
                          "Asset type (e.g., 'Material', 'Folder') - required for 'create'."] | None = None,
    properties: Annotated[dict[str, Any] | str,
                          "Dictionary (or JSON string) of properties for 'create'/'modify'."] | None = None,
    destination: Annotated[str,
                           "Target path for 'duplicate'/'move'."] | None = None,
    generate_preview: Annotated[bool,
                                "Generate a preview/thumbnail for the asset when supported."] = False,
    search_pattern: Annotated[str,
                              "Search pattern (e.g., '*.prefab')."] | None = None,
    filter_type: Annotated[str, "Filter type for search"] | None = None,
    filter_date_after: Annotated[str,
                                 "Date after which to filter"] | None = None,
    page_size: Annotated[int | float | str,
                         "Page size for pagination"] | None = None,
    page_number: Annotated[int | float | str,
                           "Page number for pagination"] | None = None,
) -> dict[str, Any]:
    # Get active instance from session state
    # Removed session_state import
    unity_instance = get_unity_instance_from_context(ctx)
    # Coerce 'properties' from JSON string to dict for client compatibility
    # FastMCP may pass dicts directly (which we use as-is) or strings (which we parse)
    if isinstance(properties, str):
        # Debug: log what we received
        ctx.info(f"manage_asset: received properties as string (first 100 chars): {properties[:100]}")
        # Try parsing as JSON first
        try:
            properties = json.loads(properties)
            ctx.info("manage_asset: coerced properties from JSON string to dict")
        except json.JSONDecodeError as json_err:
            # If JSON parsing fails, it might be a Python dict string representation
            # Try using ast.literal_eval as a fallback (safer than eval)
            try:
                import ast
                properties = ast.literal_eval(properties)
                ctx.info("manage_asset: coerced properties from Python dict string to dict")
            except (ValueError, SyntaxError) as eval_err:
                # If both fail, log warning and leave as string - Unity side may handle or provide defaults
                ctx.info(f"manage_asset: failed to parse properties string. JSON error: {json_err}, eval error: {eval_err}. Leaving as-is for Unity to handle.")
    elif isinstance(properties, dict):
        # Already a dict, use as-is
        ctx.info(f"manage_asset: received properties as dict with keys: {list(properties.keys())}")
    elif properties is not None:
        ctx.info(f"manage_asset: received properties as unexpected type: {type(properties)}")
    # Ensure properties is a dict if None
    if properties is None:
        properties = {}

    # Coerce numeric inputs defensively
    def _coerce_int(value, default=None):
        if value is None:
            return default
        try:
            if isinstance(value, bool):
                return default
            if isinstance(value, int):
                return int(value)
            s = str(value).strip()
            if s.lower() in ("", "none", "null"):
                return default
            return int(float(s))
        except Exception:
            return default

    page_size = _coerce_int(page_size)
    page_number = _coerce_int(page_number)

    # Prepare parameters for the C# handler
    params_dict = {
        "action": action.lower(),
        "path": path,
        "assetType": asset_type,
        "properties": properties,
        "destination": destination,
        "generatePreview": generate_preview,
        "searchPattern": search_pattern,
        "filterType": filter_type,
        "filterDateAfter": filter_date_after,
        "pageSize": page_size,
        "pageNumber": page_number
    }

    # Remove None values to avoid sending unnecessary nulls
    params_dict = {k: v for k, v in params_dict.items() if v is not None}

    # Get the current asyncio event loop
    loop = asyncio.get_running_loop()

    # Use centralized async retry helper with instance routing
    result = await send_with_unity_instance(async_send_command_with_retry, unity_instance, "manage_asset", params_dict, loop=loop)
    # Return the result obtained from Unity
    return result if isinstance(result, dict) else {"success": False, "message": str(result)}
