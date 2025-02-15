# chat_server/authentication.py
"""
Authentication Module
====================

This module handles user authentication and session management for the chat server.

Key Features:
- User credential validation from users.txt
- Session management and timeout handling
- Prevention of duplicate logins
- Thread-safe authentication operations
- Automatic cleanup of failed authentication attempts

Classes:
    Authentication: Manages user authentication and session lifecycle

Usage:
    auth = Authentication(users, clients, lock, logger, message_handler, network_manager)
    is_authenticated = auth.authenticate_client(client_socket)

Author: Chayan Kumawat
Date: January 2025
Version: 1.0
"""
import socket
import logging
import time
import select
from typing import Optional, Tuple

class Authentication:
    def __init__(self, users, clients, lock, logger, message_handler, network_manager):
        self.users = users
        self.clients = clients
        self.lock = lock
        self.logger = logger
        self.message_handler = message_handler
        self.network_manager = network_manager
        self.load_users()  # Load users when initializing
        self.AUTH_TIMEOUT = 30

    def load_users(self):
        try:
            self.logger.info("Loading users from users.txt")
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            users_file = os.path.join(os.path.dirname(script_dir), 'users.txt')
            with open(users_file, 'r') as f:
                for line in f:
                    username, password = line.strip().split(':')
                    self.users[username] = password
            self.logger.info(f"Successfully loaded {len(self.users)} users")
        except FileNotFoundError:
            self.logger.warning("users.txt not found - starting with empty user database")

    def authenticate_client(self, client_socket: socket.socket) -> bool:
        """Authenticate a client connection with timeout and error handling"""
        try:
            # Set socket timeout for authentication
            client_socket.settimeout(self.AUTH_TIMEOUT)
            
            # Get username with timeout
            client_socket.send("Enter username: ".encode())
            readable, _, _ = select.select([client_socket], [], [], self.AUTH_TIMEOUT)
            if not readable:
                self.logger.error("Authentication timeout waiting for username")
                return False
                
            username = client_socket.recv(1024).decode().strip()
            if not username:
                self.logger.info("Empty username received")
                client_socket.send("Invalid username.\n".encode())
                return False

            self.logger.info(f"User attempting to log in: {username}")

            # Check if user exists
            if username not in self.users:
                self.logger.info(f"Login failed - username {username} not found")
                client_socket.send("Invalid username or password.\n".encode())
                return False

            # Check for existing connection with lock
            with self.lock:
                if self._check_existing_connection(username, client_socket):
                    return False

            # Get password with timeout
            client_socket.send("Enter password: ".encode())
            readable, _, _ = select.select([client_socket], [], [], self.AUTH_TIMEOUT)
            if not readable:
                self.logger.error("Authentication timeout waiting for password")
                return False

            password = client_socket.recv(1024).decode().strip()
            
            # Verify credentials
            if self.users[username] != password:
                self.logger.info(f"Login failed - incorrect password for {username}")
                client_socket.send("Invalid username or password.\n".encode())
                return False

            # Register new client with lock
            with self.lock:
                # Double check no race condition
                if self._check_existing_connection(username, client_socket):
                    return False
                
                # Add to active clients
                self.clients[client_socket] = username
                self.network_manager.update_heartbeat(client_socket)

            # Send welcome messages
            try:
                client_socket.send("Welcome to the chat server!\n".encode())
                self.message_handler.server_broadcast(f"{username} has joined the chat.\n", {client_socket})
                self.logger.info(f"User {username} successfully authenticated and joined")
                return True
            except Exception as e:
                self.logger.error(f"Error sending welcome message: {str(e)}")
                self._cleanup_client(client_socket, username)
                return False

        except socket.timeout:
            self.logger.error("Authentication timeout")
            return False
        except ConnectionError as e:
            self.logger.error(f"Connection error during authentication: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return False
        finally:
            # Reset socket timeout to blocking mode
            client_socket.settimeout(None)

    def _check_existing_connection(self, username: str, client_socket: socket.socket) -> bool:
        """Check for existing connection and handle cleanup"""
        for sock, name in self.clients.items():
            if name == username:
                try:
                    # Try to ping existing connection
                    sock.send(b"ping")
                    client_socket.send("This username is already logged in.\n".encode())
                    self.logger.info(f"Login rejected - {username} already active")
                    return True
                except:
                    # Clean up stale connection
                    self.logger.info(f"Removing stale connection for {username}")
                    self.network_manager.disconnect_client(sock)
        return False

    def _cleanup_client(self, client_socket: socket.socket, username: str):
        """Clean up client resources on failed authentication"""
        with self.lock:
            if client_socket in self.clients:
                del self.clients[client_socket]
        self.network_manager.disconnect_client(client_socket)

    def _receive_with_timeout(self, client_socket: socket.socket) -> Optional[str]:
        """Receive data with timeout"""
        try:
            ready = select.select([client_socket], [], [], self.AUTH_TIMEOUT)
            if not ready[0]:
                self.logger.error("Authentication timeout")
                return None
            data = client_socket.recv(1024).decode().strip()
            return data if data else None
        except Exception as e:
            self.logger.error(f"Error receiving data: {str(e)}")
            return None

    def _get_input(self, client_socket: socket.socket, prompt: str) -> bool:
        """Send prompt and verify it was sent"""
        try:
            client_socket.send(prompt.encode())
            return True
        except Exception as e:
            self.logger.error(f"Error sending prompt: {str(e)}")
            return False

    def _is_user_logged_in(self, username: str) -> bool:
        """Check if user is already logged in"""
        return username in self.clients.values()