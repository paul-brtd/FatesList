"""
API v2 beta 2

This is part of Fates List. You can use this in any library you wish. For best API compatibility, just plug this directly in your Fates List library. It has no dependencies other than pydantic, typing and uuid (typing and uuid is builtin)

Depends: enums.py
"""

from fastapi import Form as FForm
from typing import Optional, List, Dict
from pydantic import BaseModel
import sys
sys.path.append("modules/models") # Libraries should remove this
import enums # as enums (for libraries)
