"""
Backward-compatible import for the Alexa Media base entity.

SPDX-License-Identifier: Apache-2.0

The implementation lives in entity.py. This module stays as a compatibility
shim for integrations and tests that imported AlexaMedia from here.
"""

from alexapy import hide_email

from .entity import AlexaMedia

__all__ = ["AlexaMedia", "hide_email"]
