# chat_server/network.py
"""
Network Manager Module
====================

This module handles all network operations for the chat server application.

Key Features:
- TCP socket management and configuration
- Client connection handling and tracking
- Message queuing and delivery
- Heartbeat monitoring
- Thread-safe network operations
- Connection timeout handling

Classes:
    NetworkManager: Manages all network communication and client connections

Usage:
    network = NetworkManager(host='127.0.0.1', port=12345)
    server_socket = network.start()
    network.handle_client(client_socket)

Author: Chayan Kumawat
Date: January 2025
Version: 1.0
"""
import socket
import threading
import logging
from typing import Dict, Set
import queue
import time  

class NetworkManager:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Client management
        self.clients: Dict[socket.socket, str] = {}
        self.active_connections: Set[socket.socket] = set()
        self.message_queues: Dict[socket.socket, queue.Queue] = {}
        self.last_heartbeat: Dict[socket.socket, float] = {}
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the server socket"""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)
        return self.server_socket

    def accept_connection(self):
        """Accept new client connection"""
        client_socket, client_address = self.server_socket.accept()
        with self.lock:
            self.active_connections.add(client_socket)
            self.message_queues[client_socket] = queue.Queue()
            self.last_heartbeat[client_socket] = time.time()
        return client_socket, client_address

    def disconnect_client(self, client_socket: socket.socket):
        """Safely disconnect a client and clean up resources"""
        with self.lock:
            try:
                if client_socket in self.clients:
                    username = self.clients[client_socket]
                    self.logger.info(f"Disconnecting user {username}")
                    
                    # Remove from all tracking collections
                    self.active_connections.discard(client_socket)
                    del self.clients[client_socket]
                    if client_socket in self.last_heartbeat:
                        del self.last_heartbeat[client_socket]
                    if client_socket in self.message_queues:
                        del self.message_queues[client_socket]
                    
                    try:
                        client_socket.shutdown(socket.SHUT_RDWR)
                        client_socket.close()
                    except:
                        pass  # Socket might already be closed
                    
                    self.logger.info(f"Successfully disconnected {username}")
                    return True
            except Exception as e:
                self.logger.error(f"Error during client disconnection: {str(e)}")
            return False

    def update_heartbeat(self, client_socket: socket.socket):
        """Update last heartbeat time for client"""
        with self.lock:
            if client_socket in self.active_connections:
                self.last_heartbeat[client_socket] = time.time()

    def check_timeouts(self, timeout_seconds: int = 60):
        """Check for client timeouts"""
        current_time = time.time()
        with self.lock:
            timed_out = [
                client for client in self.active_connections
                if current_time - self.last_heartbeat.get(client, 0) > timeout_seconds
            ]
            
        for client in timed_out:
            self.logger.warning(f"Client timed out, disconnecting")
            self.disconnect_client(client)