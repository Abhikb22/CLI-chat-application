# Compiler and flags
CXX = g++
CXXFLAGS = -std=c++20 -Wall -Wextra -pedantic -pthread

# Targets
CLIENT_SRC = client_grp.cpp
CLIENT_BIN = client_grp

# Default target
.PHONY: all clean
all: $(CLIENT_BIN)

# Compile client
$(CLIENT_BIN): $(CLIENT_SRC)
	$(CXX) $(CXXFLAGS) -o $(CLIENT_BIN) $(CLIENT_SRC)

# Clean build artifacts
clean:
	rm -f $(CLIENT_BIN)
