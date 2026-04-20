include $(GNUSTEP_MAKEFILES)/common.make

TOOL_NAME = gnustep
gnustep_OBJC_FILES = main.m GSCommandContext.m GSCommandRunner.m
gnustep_RESOURCE_FILES =
GNUSTEP_PREFIX := $(GNUSTEP_MAKEFILES)/../../..
GNUSTEP_LOCAL_LIB_DIR := $(GNUSTEP_PREFIX)/Local/Library/Libraries
GNUSTEP_SYSTEM_LIB_DIR := $(GNUSTEP_PREFIX)/System/Library/Libraries
GNUSTEP_RUNTIME_LIB_DIR := $(GNUSTEP_PREFIX)/lib
ADDITIONAL_OBJCFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include
ADDITIONAL_CPPFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include
ADDITIONAL_LDFLAGS += -L$(GNUSTEP_MAKEFILES)/../../../lib -L$(GNUSTEP_MAKEFILES)/../../../lib64
# Keep release binaries relocatable: the installed launcher also sets
# LD_LIBRARY_PATH, but relative RPATH keeps direct binary smoke tests portable.
ADDITIONAL_LDFLAGS += -Wl,-rpath,'$$ORIGIN/../../../Local/Library/Libraries'
ADDITIONAL_LDFLAGS += -Wl,-rpath,'$$ORIGIN/../../../System/Library/Libraries'
ADDITIONAL_LDFLAGS += -Wl,-rpath,'$$ORIGIN/../../../lib'
ADDITIONAL_LDFLAGS += -Wl,-rpath,'$$ORIGIN/../../../lib64'
GNUSTEP_CLI_DISPATCH_LIB := $(firstword \
  $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib/libdispatch.so) \
  $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib64/libdispatch.so) \
  $(wildcard /usr/local/lib/libdispatch.so) \
  $(wildcard /usr/lib/x86_64-linux-gnu/libdispatch.so) \
  $(wildcard /usr/lib/libdispatch.so))
GNUSTEP_CLI_BLOCKS_RUNTIME_LIB := $(firstword \
  $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib/libBlocksRuntime.so) \
  $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib64/libBlocksRuntime.so) \
  $(wildcard /usr/local/lib/libBlocksRuntime.so) \
  $(wildcard /usr/lib/x86_64-linux-gnu/libBlocksRuntime.so) \
  $(wildcard /usr/lib/libBlocksRuntime.so))
ifneq ($(GNUSTEP_CLI_DISPATCH_LIB),)
ADDITIONAL_TOOL_LIBS += -ldispatch
endif
ifneq ($(GNUSTEP_CLI_BLOCKS_RUNTIME_LIB),)
ADDITIONAL_TOOL_LIBS += -lBlocksRuntime
endif
# MSYS2 libdispatch on Windows expects mode_t to be treated as already available.
ADDITIONAL_OBJCFLAGS += -DHAVE_MODE_T
ADDITIONAL_CPPFLAGS += -DHAVE_MODE_T

include $(GNUSTEP_MAKEFILES)/tool.make
