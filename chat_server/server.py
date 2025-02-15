# chat_server/server.py
"""
Chat Server Module
================

Core server module that orchestrates all chat server components and operations.

Key Features:
- Multi-threaded client handling
- Component management (auth, messages, groups)
- Graceful shutdown handling
- Signal management
- Resource cleanup
- Thread-safe operations
- Queue-based message processing

Classes:
    ChatServer: Main server class that coordinates all chat operations

Dependencies:
    - Authentication: User validation and session management
    - MessageHandler: Message routing and delivery
    - GroupManager: Chat group operations
    - NetworkManager: Socket and connection handling
    - CommandProcessor: Client command interpretation
    - Logger: System-wide logging

Usage:
    server = ChatServer(host='127.0.0.1', port=12345)
    server.start()

Author: Chayan Kumawat
Date: January 2025
Version: 1.0
"""

import socket
import threading
import signal
import sys
from typing import Dict, Set
import queue
from .logger import setup_logging
from .authentication import Authentication
from .message_handler import MessageHandler
from .group_manager import GroupManager
from .network import NetworkManager
from .command_processor import CommandProcessor

class ChatServer:
    def __init__(self, host='127.0.0.1', port=12345):
        self.logger = setup_logging()
        self.network_manager = NetworkManager(host, port)
        self.clients: Dict[socket.socket, str] = {}
        self.users: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.message_queues = {}
        self.running = True
        
        self.message_handler = MessageHandler(self.clients, self.lock, self.logger)
        self.group_manager = GroupManager(self.clients, self.lock, self.logger, self.message_handler)
        self.command_processor = CommandProcessor(self.clients, self.lock, self.logger, self.message_handler, self.group_manager, self.network_manager)
        self.authentication = Authentication(self.users, self.clients, self.lock, self.logger, self.message_handler, self.network_manager)
        
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        self.logger.info("Server shutdown initiated")
        self.running = False
        
        with self.lock:
            # Copy client list to avoid modification during iteration
            clients_to_disconnect = list(self.clients.keys())
            for client_socket in clients_to_disconnect:
                self.network_manager.disconnect_client(client_socket)
        
        self.logger.info("Server shutdown complete")
        sys.exit(0)

    def start(self):
        self.authentication.load_users()
        server_socket = self.network_manager.start()
        self.logger.info(f"Server started on {self.network_manager.host}:{self.network_manager.port}")

        while self.running:  # Check running flag
            try:
                client_socket, client_address = self.network_manager.accept_connection()
                self.logger.info(f"New connection from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    self.logger.error(f"Error accepting connection: {e}")

    def handle_client(self, client_socket: socket.socket):
        try: 
            if not self.authentication.authenticate_client(client_socket):
                client_socket.close()
                return
            
            username = self.clients[client_socket]
            self.message_queues[client_socket] = queue.Queue()

            # Start message receiver thread 
            receiver_thread = threading.Thread(target=self.receive_messages, args=(client_socket,))
            receiver_thread.daemon = True
            receiver_thread.start()

            while True: 
                try: 
                    message = self.message_queues[client_socket].get(timeout=0.1)
                    self.command_processor.process_command(client_socket, message)
                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"Error handling client message: {str(e)}")
                    break
        finally:
            self.network_manager.disconnect_client(client_socket)

    def receive_messages(self, client_socket: socket.socket): 
        """Receives messages from client and puts them in message queue"""
        while True:
            try:
                message = client_socket.recv(1024).decode().strip()
                if not message:
                    self.logger.info(f"Empty message received, disconnecting client")
                    break
                    
                if client_socket in self.message_queues:
                    self.message_queues[client_socket].put(message)
                    self.logger.debug(f"Message queued from {self.clients[client_socket]}: {message}")
                else:
                    self.logger.warning(f"No message queue for client, possibly disconnected")
                    break
                    
            except ConnectionError as e:
                self.logger.error(f"Connection error: {str(e)}")
                break
            except Exception as e:
                self.logger.error(f"Error receiving message: {str(e)}")
                break
                
        self.network_manager.disconnect_client(client_socket)

if __name__ == "__main__":
    server = ChatServer()
    server.start()