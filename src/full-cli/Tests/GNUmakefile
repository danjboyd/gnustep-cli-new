include $(GNUSTEP_MAKEFILES)/common.make

BUNDLE_NAME = FullCLITests
NEEDS_GUI = no

FullCLITests_OBJC_FILES = \
  FullCLITestSupport.m \
  GSCommandContextTests.m \
  GSCommandRunnerTests.m \
  GSCommandWorkflowTests.m
FullCLITests_INCLUDE_DIRS = -I.. -I.
FullCLITests_BUNDLE_LIBS += -lXCTest
FullCLITests_RESOURCE_FILES =

include $(GNUSTEP_MAKEFILES)/bundle.make
