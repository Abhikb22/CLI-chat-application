
## Prerequisites
- Python 3.8+ for server
- C++ compiler (g++ 9.0+) for client
- POSIX-compliant system (Linux/Unix)
- Make build system

## Compilation
```bash
# remove if the client binary is already there 
rm -f client_grp

# Compile both server and client
make 
```

## Starting the Server
```bash
# Start the server on default port 12345
python3 -m chat_server.server
```

## Connecting Clients
```bash
# Connect to server on localhost
./client_grp
```
