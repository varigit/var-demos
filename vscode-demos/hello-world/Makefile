# Default C compiler to be used if CC is not already set in the environment
CC ?= gcc

# Default flags for the C compiler if CFLAGS is not already set in the
# environment. -Wall and -Wextra turn on all and extra warnings respectively.
CFLAGS ?= -Wall -Wextra

# Flags for compiling with debugging information and optimizations that do not
# interfere with debugging.
DEBUGFLAGS = -Og -g

# The name of the target executable.
TARGET = hello-world

# The object file(s) needed to create the target executable.
OBJECTS = $(TARGET).o

# .PHONY is used to specify targets that are not files.
# 'all' and 'clean' do not represent files, but are targets that the user
# can call.
.PHONY: all clean

# The default target ('all') depends on $(TARGET) which is 'hello-world' in
# this case.
all: $(TARGET)

# The target executable depends on the object file(s).
# The command compiles and links the object file(s) to produce the target
# executable.
# $@ and $^ are automatic variables in make.
# $@ represents the target of the rule and $^ represents all dependencies of
# the rule.
$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $(DEBUGFLAGS) -o $@ $^

# The object file(s) depend on the corresponding .c file.
# The command compiles the .c file to produce the object file.
# Again, $@ represents the target of the rule and $^ represents all
# dependencies of the rule.
$(OBJECTS): $(TARGET).c
	$(CC) $(CFLAGS) $(DEBUGFLAGS) -c -o $@ $^

# The 'clean' target has no dependencies and is used to remove the created
# files.
clean:
	rm -f $(TARGET) $(OBJECTS)
