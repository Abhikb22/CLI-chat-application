"""
Command Processing System for Chat Server
=======================================

This module implements a command-based architecture for handling various chat server operations.
It uses the Command pattern to encapsulate different chat operations into separate handler classes.

Key Components:
- CommandHandler: Abstract base class for all command handlers
- Various concrete command handlers for specific operations
- CommandProcessor: Central processor that routes commands to appropriate handlers

Thread Safety:
All operations that modify shared state are protected by locks to ensure thread safety.

Author: Chayan Kumawat
Date: January 2025
Version: 1.0
"""
import logging
import socket
from abc import ABC, abstractmethod
from typing import Dict, Set, Optional
from threading import Lock
from .message_handler import MessageHandler
from .group_manager import GroupManager
from .network import NetworkManager

class CommandHandler(ABC):
    """Abstract base class defining the interface for all command handlers."""
    
    @abstractmethod
    def execute(self, client_socket: socket.socket, *args):
        """Execute the command with given arguments."""
        pass

class PrivateMessageHandler(CommandHandler):
    """Handles private messages between users."""
    
    def __init__(self, message_handler: MessageHandler):
        self.message_handler = message_handler

    def execute(self, client_socket: socket.socket, *args):
        if len(args) < 2:
            client_socket.send("Usage: /msg <username> <message>\n".encode())
            return
        target_username, *message_parts = args
        message = ' '.join(message_parts)
        self.message_handler.private_message(client_socket, target_username, message)

class BroadcastHandler(CommandHandler):
    """Handles broadcasting messages to all connected users."""
    
    def __init__(self, message_handler: MessageHandler):
        self.message_handler = message_handler

    def execute(self, client_socket: socket.socket, *args):
        if not args:
            client_socket.send("Usage: /broadcast <message>\n".encode())
            return
        message = ' '.join(args)
        self.message_handler.broadcast_message(message, client_socket)

class CreateGroupHandler(CommandHandler):
    """Handles group creation."""
    
    def __init__(self, group_manager: GroupManager):
        self.group_manager = group_manager

    def execute(self, client_socket: socket.socket, *args):
        if len(args) != 1:
            client_socket.send("Usage: /create_group <group_name>\n".encode())
            return
        self.group_manager.create_group(client_socket, args[0])

class JoinGroupHandler(CommandHandler):
    """Handles joining a group."""
    
    def __init__(self, group_manager: GroupManager):
        self.group_manager = group_manager

    def execute(self, client_socket: socket.socket, *args):
        if len(args) != 1:
            client_socket.send("Usage: /join_group <group_name>\n".encode())
            return
        self.group_manager.join_group(client_socket, args[0])

class LeaveGroupHandler(CommandHandler):
    """Handles leaving a group."""
    
    def __init__(self, group_manager: GroupManager):
        self.group_manager = group_manager

    def execute(self, client_socket: socket.socket, *args):
        if len(args) != 1:
            client_socket.send("Usage: /leave_group <group_name>\n".encode())
            return
        self.group_manager.leave_group(client_socket, args[0])

class UsersHandler(CommandHandler):
    """Handles listing all online users."""
    
    def __init__(self, message_handler: MessageHandler):
        self.message_handler = message_handler

    def execute(self, client_socket: socket.socket, *args):
        self.message_handler.get_online_users(client_socket)

class ExitHandler(CommandHandler):
    """Handles user disconnection."""
    
    def __init__(self, message_handler: MessageHandler, group_manager: GroupManager, network_manager: NetworkManager):
        self.message_handler = message_handler
        self.group_manager = group_manager
        self.network_manager = network_manager

    def execute(self, client_socket: socket.socket, *args):
        self.group_manager.remove_from_all_groups(client_socket)

        # Remove from active clients list
        if client_socket in self.message_handler.clients:
            username = self.message_handler.clients[client_socket]
            del self.message_handler.clients[client_socket]
            self.message_handler.server_broadcast(f"User {username} has disconnected")
            
        self.network_manager.disconnect_client(client_socket)

class GroupMessageHandler(CommandHandler):
    """Handles sending messages to groups."""
    
    def __init__(self, group_manager: GroupManager):
        self.group_manager = group_manager

    def execute(self, client_socket: socket.socket, *args):
        if len(args) < 2:
            client_socket.send("Usage: /group_msg <group_name> <message>\n".encode())
            return
        group_name, *message_parts = args
        message = ' '.join(message_parts)
        self.group_manager.group_message(client_socket, group_name, message)

class GroupsUsersHandler(CommandHandler):
    """Handles listing all groups and their members."""
    
    def __init__(self, group_manager: GroupManager):
        self.group_manager = group_manager

    def execute(self, client_socket: socket.socket, *args):
        self.group_manager.get_all_group_users(client_socket)

class CommandProcessor:
    """Central command processing system that routes incoming commands to appropriate handlers."""
    
    def __init__(self, clients: Dict[socket.socket, str], lock: Lock, logger: logging.Logger, 
                 message_handler: MessageHandler, group_manager: GroupManager, network_manager: NetworkManager):
        self.clients = clients
        self.lock = lock
        self.logger = logger
        self.message_handler = message_handler
        self.group_manager = group_manager
        self.network_manager = network_manager
        self.command_handlers = self._initialize_command_handlers()

    def _initialize_command_handlers(self) -> Dict[str, CommandHandler]:
        """Initialize and return a mapping of command strings to their handlers."""
        return {
            '/msg': PrivateMessageHandler(self.message_handler),
            '/broadcast': BroadcastHandler(self.message_handler),
            '/create_group': CreateGroupHandler(self.group_manager),
            '/join_group': JoinGroupHandler(self.group_manager),
            '/group_msg': GroupMessageHandler(self.group_manager),
            '/leave_group': LeaveGroupHandler(self.group_manager),
            '/users': UsersHandler(self.message_handler),
            '/groups_users': GroupsUsersHandler(self.group_manager),
            '/exit': ExitHandler(self.message_handler, self.group_manager, self.network_manager)
        }

    def process_command(self, client_socket: socket.socket, message: str):
        """Process an incoming command from a client."""
        username = self.clients.get(client_socket, "Unknown")
        parts = message.strip().split()
        command = parts[0].lower() if parts else ""

        if command in self.command_handlers:
            self.logger.info(f"User {username} executing command: {command}")
            handler = self.command_handlers[command]
            handler.execute(client_socket, *parts[1:])
        else:
            self._send_help_message(client_socket)

    def _send_help_message(self, client_socket: socket.socket):
        """Sends a help message when an unknown command is received."""
        help_message = """
Available commands:
/msg <username> <message> - Send private message to user
/broadcast <message> - Broadcast message to all users
/create_group <group_name> - Create a new group
/join_group <group_name> - Join an existing group
/group_msg <group_name> <message> - Send message to group
/leave_group <group_name> - Leave a group
/users - List all online users
/groups_users - List all groups and their members
/exit - Disconnect from server
        """
        client_socket.send(help_message.encode())