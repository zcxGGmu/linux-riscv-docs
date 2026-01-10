# Makefile for RISC-V VDSO Time Caching Benchmark
# Build: make
# Clean: make clean

CC = gcc
CFLAGS = -Wall -O2 -g
LDFLAGS = -lrt

TARGET = vdso_cache_benchmark
SOURCE = vdso_cache_benchmark.c

.PHONY: all clean check help install test

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE) $(LDFLAGS)

clean:
	rm -f $(TARGET) *.o

check: $(TARGET)
	@echo "Running VDSO cache benchmark..."
	@./$(TARGET)

help:
	@echo "RISC-V VDSO Time Caching Benchmark"
	@echo ""
	@echo "Targets:"
	@echo "  all     - Build benchmark (default)"
	@echo "  clean   - Remove built files"
	@echo "  check   - Build and run benchmark"
	@echo "  help    - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make              # Build benchmark"
	@echo "  sudo ./$(TARGET) # Run benchmark (requires root for accurate timing)"
	@echo ""
	@echo "Note: Run as root or with appropriate permissions for best results"

install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/

test: check
