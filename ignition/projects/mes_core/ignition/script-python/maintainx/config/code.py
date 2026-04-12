"""
MaintainX API Configuration
============================
Ignition Gateway Script Library: maintainx.config

Central configuration for the MaintainX REST API integration.
All modules import their settings from here.

Setup:
  1. Replace API_KEY with your MaintainX API key
  2. When ready for production, switch to tag-based key storage
     by uncommenting the tag read and commenting the hardcoded key

MaintainX API Docs: https://api.getmaintainx.com/v1/docs
"""

# =============================================================================
# API CONNECTION
# =============================================================================

BASE_URL = "https://api.getmaintainx.com/v1"

# --- API Key: Hardcoded for Testing ---
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEzMDE0NTMsIm9yZ2FuaXphdGlvbklkIjo1MTQxOTIsImlhdCI6MTc3NDEzNDg2Miwic3ViIjoiUkVTVF9BUElfQVVUSCIsImp0aSI6IjYyOWQ5MTE4LTlkY2MtNDk5NS1hZmY3LTg4YWZkMzhjYzliNCJ9.7qQsAB7DOyIzqmSrvYudBifnCX7bK8gVVx9IbTV4W4s"

# --- API Key: Tag-Based for Production (uncomment when ready) ---
# API_KEY = str(system.tag.readBlocking(["[System]MaintainX/APIKey"])[0].value)

# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

# Default number of records to return per page
DEFAULT_LIMIT = 50

# Maximum pages to iterate when paginating (safety limit)
MAX_PAGES = 100

# Delay between paginated requests in milliseconds (rate limit protection)
PAGE_DELAY_MS = 100

# Retry settings for 429 rate limit responses
MAX_RETRIES = 3
RETRY_DELAY_MS = 2000

# =============================================================================
# RESPONSE KEY MAPPINGS
# =============================================================================
# MaintainX wraps responses differently per endpoint.
# These mappings tell the client how to extract data from each response.

# LIST endpoints return: {"resourceKey": [...], "nextCursor": "..."}
LIST_KEYS = {
	"workorders":    "workOrders",
	"workrequests":  "workRequests",
	"assets":        "assets",
	"locations":     "locations",
	"users":         "users",
	"parts":         "parts",
	"procedures":    "procedures",
	"teams":         "teams"
}

# GET/POST single-resource endpoints return: {"resourceKey": {...}}
DETAIL_KEYS = {
	"workorders":    "workOrder",
	"workrequests":  "workRequest",
	"assets":        "asset",
	"locations":     "location",
	"users":         "user",
	"parts":         "part",
	"procedures":    "procedure"
}

# POST create endpoints - some return full object, some just return {"id": ...}
# This maps which ones return only an ID
POST_ID_ONLY = ["workrequests"]

# =============================================================================
# ENUMS / CONSTANTS
# =============================================================================

# Work Order Statuses
class WOStatus:
	OPEN = "OPEN"
	IN_PROGRESS = "IN_PROGRESS"
	ON_HOLD = "ON_HOLD"
	DONE = "DONE"

# Work Order Priorities
class Priority:
	NONE = "NONE"
	LOW = "LOW"
	MEDIUM = "MEDIUM"
	HIGH = "HIGH"

# Assignee Types
class AssigneeType:
	USER = "USER"
	TEAM = "TEAM"

# Work Order Categories (common ones - MaintainX allows custom categories)
class Categories:
	INSPECTION = "Inspection"
	DAMAGE = "Damage"
	ELECTRICAL = "Electrical"
	MECHANICAL = "Mechanical"
	PREVENTIVE = "Preventive Maintenance"
	SAFETY = "Safety"