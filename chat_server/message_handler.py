# chat_server/message_handler.py
"""
Message Handler Module
====================

This module implements message handling and routing for the chat server application.

Key Features:
- Private message delivery between users
- Broadcast messaging to all connected clients
- Server announcements and notifications
- Online user listing functionality
- Thread-safe message operations
- Error handling and logging

Classes:
    MessageHandler: Manages all message routing and delivery operations

Usage:
    handler = MessageHandler(clients, lock, logger, network_manager)
    handler.broadcast_message("Hello everyone")
    handler.private_message(sender, "user1", "Hello")

Author: Chayan Kumawat
Date: January 2025
Version: 1.0
"""
import socket 
import logging

class MessageHandler:
    def __init__(self, clients, lock, logger, network_manager=None):
        self.clients = clients
        self.lock = lock
        self.logger = logger
        self.network_manager = network_manager
    
    def get_online_users(self, client_socket: socket.socket):
        """Lists all currently online users."""
        with self.lock:
            online_users = list(self.clients.values())
            response = "Online users:\n" + "\n".join(online_users)
            client_socket.send(response.encode())
            requesting_user = self.clients.get(client_socket, "Unknown")
            self.logger.info(f"User {requesting_user} requested list of online users")
    
        
    def broadcast_message(self, message: str, sender_socket=None):
        sender_username = self.clients[sender_socket] if sender_socket else "Server"
        formatted_message = f"[Broadcast][{sender_username}]: {message}"
        self.logger.info(f"Broadcast by {sender_username}")
        for client_socket in self.clients:
            if client_socket == sender_socket:
                continue
            client_socket.send(formatted_message.encode())
        if sender_socket:
            self.logger.info("Broadcasted successfully")
            sender_socket.send(f"Message broadcast successful\n{formatted_message}".encode())

    def server_broadcast(self, message: str, exception_clients = set()):
        for client_socket in self.clients:
            if client_socket not in exception_clients:
                client_socket.send(message.encode())

    def private_message(self, sender_socket: socket.socket, target_username: str, message: str):
        with self.lock:
            sender_username = self.clients.get(sender_socket)

            for client_socket, username in self.clients.items():
                if username == target_username:
                    try:
                        client_socket.send(f"[{sender_username}]: {message}".encode())
                        self.logger.info(f"Private message delivered: {sender_username} -> {target_username}")
                        return True
                    except Exception as e:
                        self.disconnect_client(client_socket)
                        sender_socket.send(f"Message cannot be sent to user {target_username}: {str(e)}\n".encode())
                        self.logger.error(f"Failed to send private message from {sender_username} to {target_username}: {str(e)}")
                        return False
            
            sender_socket.send(f"User {target_username} not found online\n".encode())
            self.logger.warning(f"Private message failed: {target_username} not found (sender: {sender_username})")
            return False

    def disconnect_client(self, client_socket: socket.socket):
        """Handle client disconnection"""
        with self.lock:
            try:
                if client_socket in self.clients:
                    username = self.clients[client_socket]
                    self.logger.info(f"User {username} disconnecting")
                    
                    # Remove from clients dictionary
                    del self.clients[client_socket]
                    
                    # Notify other clients
                    self.server_broadcast(f"{username} has left the chat.\n", {client_socket})
                    
                    # Close socket
                    try:
                        client_socket.close()
                    except:
                        pass
                    
                    self.logger.info(f"User {username} successfully disconnected")
            except Exception as e:
                self.logger.error(f"Error during client disconnection: {str(e)}")