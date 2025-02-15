# stress_test.py
import socket
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor

class ChatClientTester:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        # Test users from users.txt
        self.test_users = [
            ('alice', 'password123'),
            ('bob', 'qwerty456'),
            ('charlie', 'pass789'),
            ('frank', 'letmein')
        ]
        
    def connect_client(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        return sock

    def login_user(self, sock, username, password):
        # Handle login
        sock.recv(1024)  # "Enter username: "
        sock.send(username.encode())
        sock.recv(1024)  # "Enter password: "
        sock.send(password.encode())
        response = sock.recv(1024).decode()
        return "Welcome" in response

    def run_client_session(self, username, password):
        try:
            sock = self.connect_client()
            if not self.login_user(sock, username, password):
                print(f"Login failed for {username}")
                return False

            # Test sequence of commands
            commands = [
                f"/create_group group_{username}",
                "/users",
                f"/broadcast Hello from {username}",
                f"/group_msg group_{username} Test message",
                "/groups_users",
                f"/leave_group group_{username}"
            ]

            for cmd in commands:
                sock.send(cmd.encode())
                time.sleep(0.1)  # Small delay between commands
                response = sock.recv(1024).decode()
                print(f"{username} - {cmd}: {response[:50]}...")

            return True
        except Exception as e:
            print(f"Error in client session {username}: {str(e)}")
            return False
        finally:
            sock.close()

    def stress_test(self, num_concurrent=10, duration=60):
        print(f"Starting stress test with {num_concurrent} concurrent clients")
        start_time = time.time()
        success_count = 0
        total_operations = 0

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            while time.time() - start_time < duration:
                # Randomly select test users
                username, password = random.choice(self.test_users)
                future = executor.submit(self.run_client_session, username, password)
                if future.result():
                    success_count += 1
                total_operations += 1

        print(f"\nStress Test Results:")
        print(f"Duration: {duration} seconds")
        print(f"Concurrent Clients: {num_concurrent}")
        print(f"Total Operations: {total_operations}")
        print(f"Successful Operations: {success_count}")
        print(f"Success Rate: {(success_count/total_operations)*100:.2f}%")
        print(f"Operations/Second: {total_operations/duration:.2f}")

def run_correctness_test():
    tester = ChatClientTester()
    print("Running correctness tests...")

    # Test 1: Authentication
    print("\nTest 1: Authentication")
    sock = tester.connect_client()
    result = tester.login_user(sock, "alice", "password123")
    print(f"Valid login test: {'PASS' if result else 'FAIL'}")
    sock.close()

    # Test 2: Invalid Authentication
    print("\nTest 2: Invalid Authentication")
    sock = tester.connect_client()
    result = tester.login_user(sock, "alice", "wrongpass")
    print(f"Invalid login test: {'PASS' if not result else 'FAIL'}")
    sock.close()

    # Test 3: Group Operations
    print("\nTest 3: Group Operations")
    test_sequence = [
        ("alice", "password123", [
            "/create_group testgroup",
            "/group_msg testgroup Hello group",
            "/leave_group testgroup"
        ]),
        ("bob", "qwerty456", [
            "/join_group testgroup",
            "/group_msg testgroup Hello from Bob"
        ])
    ]

    for username, password, commands in test_sequence:
        sock = tester.connect_client()
        if tester.login_user(sock, username, password):
            for cmd in commands:
                sock.send(cmd.encode())
                response = sock.recv(1024).decode()
                print(f"{username} - {cmd}: {response[:50]}...")
                time.sleep(0.5)
        sock.close()

if __name__ == "__main__":
    # Run correctness tests
    run_correctness_test()

    # Run stress test
    tester = ChatClientTester()
    tester.stress_test(num_concurrent=10, duration=30)