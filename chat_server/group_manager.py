# chat_server/group_manager.py
"""
Group manager for chat server
=======================================

This module implements a secure chat group management system for a multi-user chat server.
- GroupEvent: Data class for encapsulating group-related events
- GroupOperationHandler: Abstract base class defining interface for group operations
- GroupMessageSender: Abstract base class for message sending operations
- DefaultGroupMessageSender: Concrete implementation of message sending
- GroupMembershipManager: Handles group membership operations
- GroupManager: Main class orchestrating all group-related functionality
The system prevents race conditions during group operations and handles concurrent
group management requests safely.
Classes:
    GroupEvent: Represents group-related events with group name, username, and message
    GroupOperationHandler: Abstract interface for group operations
    GroupMessageSender: Abstract interface for message sending
    DefaultGroupMessageSender: Basic implementation of message sending
    GroupMembershipManager: Manages group memberships and member operations
    GroupManager: Core class managing all group-related functionality
Features:
- Group creation and deletion
- Member management (join/leave operations)
- Group messaging
- Automatic group cleanup
- Thread-safe operations
- Failure handling and client disconnection
- Event notifications
- Comprehensive logging
Usage Example:
Error Handling:
- Validates group existence before operations
- Handles duplicate group creation attempts
- Manages invalid join/leave requests
- Handles disconnected clients
- Provides appropriate error messages
Dependencies:
- socket: For network communications
- threading: For thread synchronization
- logging: For event logging
- typing: For type hints
- dataclasses: For data class implementation
- abc: For abstract base classes

Thread Safety:
All operations that modify shared state are protected by locks to ensure thread safety.
The system prevents multiple logins with the same username and handles concurrent
authentication requests safely.

Author: Chayan Kumawat
Date: January 2025
Version: 1.0
"""

from abc import ABC, abstractmethod
import logging
from typing import Set, Dict, Optional
import socket
from dataclasses import dataclass

@dataclass
class GroupEvent:
    """Data class for group-related events"""
    group_name: str
    username: str
    message: str = ""

class GroupOperationHandler(ABC):
    """Abstract base class for group operations"""
    @abstractmethod
    def handle(self, client_socket: socket.socket, group_name: str, **kwargs) -> bool:
        pass

class GroupMessageSender(ABC):
    """Abstract base class for sending group messages"""
    @abstractmethod
    def send_message(self, socket: socket.socket, message: str) -> bool:
        pass

class DefaultGroupMessageSender(GroupMessageSender):
    def send_message(self, socket: socket.socket, message: str) -> bool:
        try:
            socket.send(message.encode())
            return True
        except:
            return False

class GroupMembershipManager:
    """Handles group membership operations"""
    def __init__(self, groups: Dict[str, Set[socket.socket]], clients: dict):
        self.groups = groups
        self.clients = clients

    def is_member(self, client_socket: socket.socket, group_name: str) -> bool:
        return group_name in self.groups and client_socket in self.groups[group_name]

    def add_member(self, client_socket: socket.socket, group_name: str) -> None:
        if group_name not in self.groups:
            self.groups[group_name] = set()
        self.groups[group_name].add(client_socket)

    def remove_member(self, client_socket: socket.socket, group_name: str) -> None:
        if self.is_member(client_socket, group_name):
            self.groups[group_name].remove(client_socket)

class GroupManager:
    """GroupManager handles group-based chat functionality in the chat server.
    This class manages creation, joining, messaging, and leaving of chat groups. It provides
    thread-safe operations for group management using locks and maintains group membership state.
    Attributes:
        groups (Dict[str, Set[socket.socket]]): Maps group names to sets of member sockets
        clients (Dict[socket.socket, str]): Maps client sockets to usernames
        lock (threading.Lock): Thread synchronization lock for group operations
        logger (Logger): Logger instance for recording events
        message_handler (MessageHandler): Handles message broadcasting
        membership_manager (GroupMembershipManager): Manages group membership operations
        message_sender (DefaultGroupMessageSender): Handles sending messages to clients
    Example:
        manager = GroupManager(clients_dict, threading_lock, logger_instance, msg_handler)
        manager.create_group(client_socket, "python_developers") 
        manager.join_group(another_socket, "python_developers")
        manager.group_message(client_socket, "python_developers", "Hello team!")
    Note:
        - All public methods are thread-safe using the lock
        - Failed message deliveries result in client disconnection
        - Group is automatically deleted when last member leaves
        - Validates group existence and membership before operations
    Implementation Details:
        - Uses composition with GroupMembershipManager for membership operations
        - Implements notification system for group events
        - Handles edge cases like duplicate joins and invalid leaves
        - Provides detailed logging for debugging and monitoring
        - Maintains consistency with synchronized access to shared state
    """
    def __init__(self, clients, lock, logger, message_handler):
        self.groups: Dict[str, Set[socket.socket]] = {}
        self.clients = clients
        self.lock = lock
        self.logger = logger
        self.message_handler = message_handler
        self.membership_manager = GroupMembershipManager(self.groups, self.clients)
        self.message_sender = DefaultGroupMessageSender()
    

    def remove_from_all_groups(self, client_socket: socket.socket) -> None:
        """Remove user from all groups they are member of."""
        with self.lock:
            username = self.clients.get(client_socket)
            if not username:
                return
                
            groups_to_delete = []
            for group_name, members in self.groups.items():
                if client_socket in members:
                    members.remove(client_socket)
                    self.logger.info(f"User {username} removed from group {group_name}")
                    
                    if not members:
                        groups_to_delete.append(group_name)
                    else:
                        # Notify remaining members
                        self._notify_group_members(
                            group_name,
                            f"[Group {group_name}]: {username} has left the group."
                        )

            # Delete empty groups
            for group_name in groups_to_delete:
                del self.groups[group_name]
                self.logger.info(f"Group {group_name} deleted - no members remaining")
        
    def get_all_group_users(self, client_socket: socket.socket):
        """Lists all groups and their members."""
        with self.lock:
            requesting_user = self.clients.get(client_socket, "Unknown")
            self.logger.info(f"User {requesting_user} requested list of groups and their members")
            
            response = "Groups and their members:\n"
            if not self.groups:
                response = "No groups exist.\n"
                self.logger.info("No groups exist when listing was requested")
            else:
                for group_name, members in self.groups.items():
                    response += f"\nGroup '{group_name}':\n"
                    member_count = len(members)
                    self.logger.info(f"Group '{group_name}' has {member_count} members")
                    for member_socket in members:
                        username = self.clients.get(member_socket, "Unknown")
                        response += f"- {username}\n"
            client_socket.send(response.encode())


    def _notify_group_members(self, group_name: str, message: str, exclude_socket: Optional[socket.socket] = None) -> None:
        """Helper method to notify group members"""
        if group_name not in self.groups:
            return

        failed_clients = set()
        for member_socket in self.groups[group_name]:
            if member_socket != exclude_socket:
                if not self.message_sender.send_message(member_socket, message):
                    failed_clients.add(member_socket)
                    self.logger.error(f"Failed to send group message to a member in group {group_name}")

        for failed_socket in failed_clients:
            self.disconnect_client(failed_socket)

    def create_group(self, client_socket: socket.socket, group_name: str) -> None:
        with self.lock:
            if group_name not in self.groups:
                self.membership_manager.add_member(client_socket, group_name)
                creator_username = self.clients[client_socket]
                self.logger.info(f"Group '{group_name}' created by {creator_username}")
                self.message_sender.send_message(client_socket, f"Group {group_name} created.")
                event = GroupEvent(group_name=group_name, username=creator_username)
                self.message_handler.server_broadcast(f"New group '{event.group_name}' has been created by {event.username}", {client_socket})
            else:
                self.message_sender.send_message(client_socket, f"Alert : Group '{group_name}' already exists.")
                self.logger.info(f"Failed to create group '{group_name}' - already exists")

    def join_group(self, client_socket: socket.socket, group_name: str) -> None:
        with self.lock:
            if not self.groups.get(group_name):
                self.logger.info(f"Failed join attempt - group '{group_name}' does not exist")
                self.message_sender.send_message(client_socket, f"Alert: Group '{group_name}' does not exist.")
                return

            if self.membership_manager.is_member(client_socket, group_name):
                self.logger.info(f"Failed join attempt - user already in group '{group_name}'")
                self.message_sender.send_message(client_socket, f"Alert: You are already a member of group '{group_name}'.")
                return

            joiner_username = self.clients[client_socket]
            self.membership_manager.add_member(client_socket, group_name)
            self.message_sender.send_message(client_socket, f"You joined the group {group_name}.")
            self._notify_group_members(
                group_name,
                f"[Group {group_name}]: {joiner_username} has joined the group.",
                client_socket
            )

    def group_message(self, sender_socket: socket.socket, group_name: str, message: str) -> None:
        with self.lock:
            if not self.membership_manager.is_member(sender_socket, group_name):
                sender_username = self.clients[sender_socket]
                self.logger.warning(f"User {sender_username} attempted to send message to group {group_name} without being a member")
                self.message_sender.send_message(sender_socket, f"Error: You are not a member of group '{group_name}'.")
                return

            sender_username = self.clients[sender_socket]
            formatted_message = f"[Group {group_name}][{sender_username}]: {message}"
            self._notify_group_members(group_name, formatted_message)

    def leave_group(self, client_socket: socket.socket, group_name: str) -> None:
        with self.lock:
            if not self.membership_manager.is_member(client_socket, group_name):
                self.logger.info(f"Failed leave attempt - user not in group '{group_name}'")
                self.message_sender.send_message(client_socket, f"You are not a member of group {group_name}.")
                return

            leaver_username = self.clients[client_socket]
            self.membership_manager.remove_member(client_socket, group_name)
            self.message_sender.send_message(client_socket, f"You left the group {group_name}.")
            
            if self.groups[group_name]:
                self._notify_group_members(
                    group_name,
                    f"[Group {group_name}]: {leaver_username} has left the group."
                )
            else:
                del self.groups[group_name]
                self.message_sender.send_message(
                    client_socket,
                    f"Group {group_name} has been deleted as you were the last remaining member."
                )
                self.message_handler.server_broadcast(
                    f"Group '{group_name}' has been deleted as it has no members.",
                    {client_socket}
                )