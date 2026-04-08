include $(GNUSTEP_MAKEFILES)/common.make

TOOL_NAME = gnustep
gnustep_OBJC_FILES = main.m GSCommandContext.m GSCommandRunner.m
gnustep_RESOURCE_FILES =
ADDITIONAL_OBJCFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include
ADDITIONAL_CPPFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include
ADDITIONAL_LDFLAGS += -L$(GNUSTEP_MAKEFILES)/../../../lib -L$(GNUSTEP_MAKEFILES)/../../../lib64
# MSYS2 libdispatch on Windows expects mode_t to be treated as already available.
ADDITIONAL_OBJCFLAGS += -DHAVE_MODE_T
ADDITIONAL_CPPFLAGS += -DHAVE_MODE_T

include $(GNUSTEP_MAKEFILES)/tool.make
