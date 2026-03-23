# Runtime configuration
DEPTH ?= 5
SRC := $(shell find . -type f -name "*.py")
TARGET := $(shell find . -name "main.py")
RUN := python3 $(TARGET) $(DEPTH)

.PHONY: all clean test run

all: result1.log result2.log test

# Run program manually
run:
	$(RUN)

# Clean build artifacts
clean:
	rm -f result*.log

# Generate logs from input streams
result%.log: $(SRC)
	$(RUN) < input$*.stream > $@

# Verify results
test: result1.log
	diff result1.log output1.log