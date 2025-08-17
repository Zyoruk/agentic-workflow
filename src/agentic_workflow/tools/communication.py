"""Communication tools for agentic workflow system."""

import json
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ..core.logging_config import get_logger
from . import Tool, ToolCapability

logger = get_logger(__name__)


class EmailTool(Tool):
    """Tool for sending emails."""

    def __init__(self):
        capabilities = ToolCapability(
            name="email_sender",
            description="Send emails via SMTP",
            category="communication",
            tags=["email", "smtp", "messaging"],
            input_schema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recipient email addresses",
                    },
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body"},
                    "smtp_server": {"type": "string", "description": "SMTP server"},
                    "smtp_port": {
                        "type": "integer",
                        "description": "SMTP port",
                        "default": 587,
                    },
                    "username": {"type": "string", "description": "SMTP username"},
                    "password": {"type": "string", "description": "SMTP password"},
                    "use_tls": {
                        "type": "boolean",
                        "description": "Use TLS",
                        "default": True,
                    },
                },
                "required": ["to", "subject", "body"],
            },
        )
        super().__init__("email_sender", capabilities)

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute email sending."""
        to_addresses = inputs["to"]
        subject = inputs["subject"]
        body = inputs["body"]
        smtp_server = inputs.get("smtp_server", "localhost")
        smtp_port = inputs.get("smtp_port", 587)
        username = inputs.get("username")
        password = inputs.get("password")
        use_tls = inputs.get("use_tls", True)

        try:
            # Create message
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["To"] = ", ".join(to_addresses)
            if username:
                msg["From"] = username

            # Add body
            msg.attach(MIMEText(body, "plain"))

            # Send email (mock implementation for safety)
            # In a real implementation, you would connect to SMTP server
            logger.info(f"Mock email sent to {to_addresses}: {subject}")

            return {
                "success": True,
                "message": f"Email sent to {len(to_addresses)} recipients",
                "recipients": to_addresses,
                "subject": subject,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipients": to_addresses,
                "subject": subject,
            }

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        required_fields = ["to", "subject", "body"]
        if not all(field in inputs for field in required_fields):
            return False

        # Validate email addresses format (basic check)
        to_addresses = inputs["to"]
        if not isinstance(to_addresses, list) or not to_addresses:
            return False

        return all("@" in addr for addr in to_addresses)


class SlackTool(Tool):
    """Tool for sending Slack messages."""

    def __init__(self):
        capabilities = ToolCapability(
            name="slack_messenger",
            description="Send messages to Slack channels",
            category="communication",
            tags=["slack", "messaging", "webhook"],
            input_schema={
                "type": "object",
                "properties": {
                    "webhook_url": {
                        "type": "string",
                        "description": "Slack webhook URL",
                    },
                    "channel": {"type": "string", "description": "Slack channel"},
                    "message": {"type": "string", "description": "Message text"},
                    "username": {"type": "string", "description": "Bot username"},
                    "emoji": {"type": "string", "description": "Bot emoji"},
                },
                "required": ["webhook_url", "message"],
            },
        )
        super().__init__("slack_messenger", capabilities)

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute Slack message sending."""
        webhook_url = inputs["webhook_url"]
        message = inputs["message"]
        channel = inputs.get("channel")
        username = inputs.get("username", "Agentic Workflow Bot")
        emoji = inputs.get("emoji", ":robot_face:")

        try:
            # Prepare Slack payload
            payload = {"text": message, "username": username, "icon_emoji": emoji}

            if channel:
                payload["channel"] = channel

            # Mock sending (in real implementation, use requests to post to webhook)
            logger.info(
                f"Mock Slack message sent to {channel or 'default channel'}: {message}"
            )

            return {
                "success": True,
                "message": "Slack message sent successfully",
                "channel": channel,
                "text": message,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": channel,
                "text": message,
            }

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        return (
            "webhook_url" in inputs
            and "message" in inputs
            and isinstance(inputs["webhook_url"], str)
            and isinstance(inputs["message"], str)
        )


class NotificationTool(Tool):
    """Tool for general notifications."""

    def __init__(self):
        capabilities = ToolCapability(
            name="notification_sender",
            description="Send notifications via multiple channels",
            category="communication",
            tags=["notification", "alert", "messaging"],
            input_schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Notification message",
                    },
                    "title": {"type": "string", "description": "Notification title"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "default": "normal",
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Notification channels",
                    },
                    "recipients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recipient identifiers",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata",
                    },
                },
                "required": ["message"],
            },
        )
        super().__init__("notification_sender", capabilities)

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute notification sending."""
        message = inputs["message"]
        title = inputs.get("title", "Notification")
        priority = inputs.get("priority", "normal")
        channels = inputs.get("channels", ["default"])
        recipients = inputs.get("recipients", [])
        metadata = inputs.get("metadata", {})

        try:
            # Create notification record
            notification = {
                "id": f"notif_{int(time.time())}",
                "title": title,
                "message": message,
                "priority": priority,
                "channels": channels,
                "recipients": recipients,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat(),
                "status": "sent",
            }

            # Mock sending to different channels
            sent_channels = []
            for channel in channels:
                logger.info(
                    f"Mock notification sent via {channel}: {title} - {message}"
                )
                sent_channels.append(channel)

            return {
                "success": True,
                "notification_id": notification["id"],
                "message": f"Notification sent via {len(sent_channels)} channels",
                "channels_used": sent_channels,
                "recipients_count": len(recipients),
                "priority": priority,
                "timestamp": notification["timestamp"],
            }

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {
                "success": False,
                "error": str(e),
                "title": title,
                "message": message,
            }

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        return "message" in inputs and isinstance(inputs["message"], str)


class WebhookTool(Tool):
    """Tool for sending webhook notifications."""

    def __init__(self):
        capabilities = ToolCapability(
            name="webhook_sender",
            description="Send webhook notifications to external services",
            category="communication",
            tags=["webhook", "http", "api", "integration"],
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Webhook URL"},
                    "payload": {"type": "object", "description": "Webhook payload"},
                    "method": {
                        "type": "string",
                        "enum": ["POST", "PUT", "PATCH"],
                        "default": "POST",
                    },
                    "headers": {"type": "object", "description": "HTTP headers"},
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout",
                        "default": 30,
                    },
                },
                "required": ["url", "payload"],
            },
        )
        super().__init__("webhook_sender", capabilities)

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute webhook sending."""
        url = inputs["url"]
        payload = inputs["payload"]
        method = inputs.get("method", "POST")
        headers = inputs.get("headers", {"Content-Type": "application/json"})
        timeout = inputs.get("timeout", 30)

        try:
            # Mock webhook sending (in real implementation, use httpx or requests)
            logger.info(f"Mock webhook {method} sent to {url}")
            logger.debug(f"Webhook payload: {json.dumps(payload, indent=2)}")

            return {
                "success": True,
                "status_code": 200,
                "message": "Webhook sent successfully",
                "url": url,
                "method": method,
                "payload_size": len(json.dumps(payload)),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return {"success": False, "error": str(e), "url": url, "method": method}

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        return (
            "url" in inputs
            and "payload" in inputs
            and isinstance(inputs["url"], str)
            and isinstance(inputs["payload"], dict)
        )


# Tool factory functions for discovery
def create_default_email_tool():
    """Create default email tool."""
    return EmailTool()


def create_default_slack_tool():
    """Create default Slack tool."""
    return SlackTool()


def create_default_notification_tool():
    """Create default notification tool."""
    return NotificationTool()


def create_default_webhook_tool():
    """Create default webhook tool."""
    return WebhookTool()
