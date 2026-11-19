/* ThemeSwitch: cycle live theme switches with a window of controls open,
   timing each switch and recording the process's working set. Arguments:
   -cycles N, then theme bundle paths ("GNUstep" for the default theme). */
#import <AppKit/AppKit.h>
#import <GNUstepGUI/GSTheme.h>
#include <windows.h>
#include <psapi.h>

static size_t
WorkingSet(void)
{
  PROCESS_MEMORY_COUNTERS counters;

  if (GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters)))
    {
      return counters.WorkingSetSize;
    }
  return 0;
}

static void
Spin(NSTimeInterval seconds)
{
  NSDate *until = [NSDate dateWithTimeIntervalSinceNow: seconds];

  while ([until timeIntervalSinceNow] > 0)
    {
      NSEvent *event = [NSApp nextEventMatchingMask: NSAnyEventMask
                                          untilDate: [NSDate dateWithTimeIntervalSinceNow: 0.02]
                                             inMode: NSDefaultRunLoopMode
                                            dequeue: YES];
      if (event != nil)
        {
          [NSApp sendEvent: event];
        }
    }
}

static NSWindow *
MakeWindow(void)
{
  NSWindow *window = [[NSWindow alloc] initWithContentRect: NSMakeRect(100, 100, 420, 320)
                                                 styleMask: NSTitledWindowMask | NSResizableWindowMask
                                                   backing: NSBackingStoreBuffered
                                                     defer: NO];
  NSView *content = [window contentView];
  NSButton *button = [[NSButton alloc] initWithFrame: NSMakeRect(20, 270, 120, 32)];
  NSTextField *field = [[NSTextField alloc] initWithFrame: NSMakeRect(160, 272, 200, 24)];
  NSSlider *slider = [[NSSlider alloc] initWithFrame: NSMakeRect(20, 230, 200, 24)];
  NSPopUpButton *popup = [[NSPopUpButton alloc] initWithFrame: NSMakeRect(240, 230, 150, 26)];
  NSScrollView *scroll = [[NSScrollView alloc] initWithFrame: NSMakeRect(20, 20, 380, 190)];
  NSTextView *text = [[NSTextView alloc] initWithFrame: NSMakeRect(0, 0, 360, 600)];
  NSBox *card = [[NSBox alloc] initWithFrame: NSMakeRect(240, 100, 160, 100)];

  [window setTitle: @"ThemeSwitch"];
  [button setTitle: @"Button"];
  [field setStringValue: @"Text"];
  [popup addItemsWithTitles: [NSArray arrayWithObjects: @"One", @"Two", nil]];
  [scroll setHasVerticalScroller: YES];
  [scroll setDocumentView: text];
  [text setString: @"Lorem ipsum\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nend"];
  [content addSubview: scroll];
  [content addSubview: button];
  [content addSubview: field];
  [content addSubview: slider];
  [content addSubview: popup];
  [content addSubview: card];
  [window makeKeyAndOrderFront: nil];
  return window;
}

int
main(int argc, const char **argv)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];
  NSArray *arguments = [[NSProcessInfo processInfo] arguments];
  NSMutableArray *themes = [NSMutableArray array];
  NSInteger cycles = 10, i, cycle;
  NSWindow *window;
  size_t startSet, afterFirst;
  NSTimeInterval worst = 0.0;
  NSString *worstName = @"";

  for (i = 1; i < (NSInteger)[arguments count]; i++)
    {
      NSString *a = [arguments objectAtIndex: i];

      if ([a isEqualToString: @"-cycles"] && i + 1 < (NSInteger)[arguments count])
        {
          cycles = [[arguments objectAtIndex: ++i] integerValue];
        }
      else if ([a hasPrefix: @"-"] == NO)
        {
          [themes addObject: a];
        }
    }
  [NSApplication sharedApplication];
  /* -preload: load every theme while the default one is active, so each
     records libs-gui's own methods as the originals it overrides. */
  if ([arguments containsObject: @"-preload"])
    {
      NSEnumerator *e = [themes objectEnumerator];
      NSString *name;

      while ((name = [e nextObject]) != nil)
        {
          [GSTheme loadThemeNamed: name];
        }
      printf("preloaded %ld themes under %s\n", (long)[themes count], [[[GSTheme theme] name] UTF8String]);
    }
  window = MakeWindow();
  Spin(0.5);
  startSet = WorkingSet();
  afterFirst = 0;
  printf("start working set %zu KB, %ld themes, %ld cycles\n",
         startSet / 1024, (long)[themes count], (long)cycles);
  fflush(stdout);
  for (cycle = 0; cycle < cycles; cycle++)
    {
      NSEnumerator *e = [themes objectEnumerator];
      NSString *name;

      while ((name = [e nextObject]) != nil)
        {
          NSAutoreleasePool *inner = [NSAutoreleasePool new];
          NSDate *start = [NSDate date];
          GSTheme *theme = [GSTheme loadThemeNamed: name];
          NSTimeInterval took;

          if (theme == nil)
            {
              printf("FAIL cycle %ld: could not load %s\n", (long)cycle, [name UTF8String]);
              fflush(stdout);
              return 2;
            }
          [GSTheme setTheme: theme];
          [window display];
          Spin(0.15);
          took = -[start timeIntervalSinceNow];
          if (took > worst)
            {
              worst = took;
              worstName = [[name lastPathComponent] retain];
            }
          if (cycle == 0)
            {
              printf("cycle 0 %s: %.0f ms, active %s\n", [[name lastPathComponent] UTF8String],
                     took * 1000.0, [[[GSTheme theme] name] UTF8String]);
              fflush(stdout);
            }
          [inner release];
        }
      if (cycle == 0)
        {
          afterFirst = WorkingSet();
        }
    }
  printf("after cycle 0 %zu KB, after %ld cycles %zu KB (growth after warm-up %ld KB, %.1f KB per cycle)\n",
         afterFirst / 1024, (long)cycles, WorkingSet() / 1024,
         (long)((long)WorkingSet() - (long)afterFirst) / 1024,
         cycles > 1 ? ((double)WorkingSet() - (double)afterFirst) / 1024.0 / (cycles - 1) : 0.0);
  printf("slowest switch %.0f ms (%s, includes 150 ms of event spin)\n", worst * 1000.0, [worstName UTF8String]);
  printf("OK\n");
  [pool release];
  return 0;
}
