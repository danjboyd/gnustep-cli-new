#import "GSCommandRunner.h"
#import "GSCommandContext.h"

@implementation GSCommandRunner

- (NSArray *)knownCommands
{
  return [NSArray arrayWithObjects:
                    @"setup",
                    @"doctor",
                    @"build",
                    @"run",
                    @"new",
                    @"install",
                    @"remove",
                    nil];
}

- (BOOL)isKnownCommand:(NSString *)command
{
  return [[self knownCommands] containsObject: command];
}

- (NSString *)commandSummary:(NSString *)command
{
  if ([command isEqualToString: @"doctor"])
    {
      return @"Inspect the local GNUstep environment and report readiness.";
    }
  if ([command isEqualToString: @"setup"])
    {
      return @"Install or repair the managed GNUstep CLI environment.";
    }
  if ([command isEqualToString: @"build"])
    {
      return @"Build the current GNUstep Make project.";
    }
  if ([command isEqualToString: @"run"])
    {
      return @"Run the current GNUstep Make project.";
    }
  if ([command isEqualToString: @"new"])
    {
      return @"Create a new GNUstep project from a curated template.";
    }
  if ([command isEqualToString: @"install"])
    {
      return @"Install a GNUstep package into the managed environment.";
    }
  if ([command isEqualToString: @"remove"])
    {
      return @"Remove a GNUstep package from the managed environment.";
    }
  return @"";
}

- (void)printCommandHelp:(NSString *)command
{
  printf("Usage:\n");
  printf("  gnustep %s [options]\n\n", [command UTF8String]);
  printf("%s\n", [[self commandSummary: command] UTF8String]);
}

- (void)printHelp
{
  NSUInteger i = 0;
  NSArray *commands = [self knownCommands];

  printf("GNUstep CLI full interface\n\n");
  printf("Usage:\n");
  printf("  gnustep <command> [options] [args]\n\n");
  printf("Global options:\n");
  printf("  --help\n");
  printf("  --version\n");
  printf("  --json\n");
  printf("  --verbose\n");
  printf("  --quiet\n");
  printf("  --yes\n\n");
  printf("Commands:\n");
  for (i = 0; i < [commands count]; i++)
    {
      NSString *command = [commands objectAtIndex: i];
      printf("  %-7s %s\n",
             [command UTF8String],
             [[self commandSummary: command] UTF8String]);
    }
}

- (NSDictionary *)payloadWithCommand:(NSString *)command
                                  ok:(BOOL)ok
                              status:(NSString *)status
                             summary:(NSString *)summary
                                data:(NSDictionary *)data
{
  NSMutableDictionary *payload = [NSMutableDictionary dictionary];
  [payload setObject: [NSNumber numberWithInt: 1] forKey: @"schema_version"];
  [payload setObject: command forKey: @"command"];
  [payload setObject: [NSNumber numberWithBool: ok] forKey: @"ok"];
  [payload setObject: status forKey: @"status"];
  [payload setObject: summary forKey: @"summary"];
  if (data != nil)
    {
      [payload setObject: data forKey: @"data"];
    }
  return payload;
}

- (void)emitJSONPayload:(NSDictionary *)payload
{
  NSData *data = [NSJSONSerialization dataWithJSONObject: payload options: 0 error: nil];
  if (data != nil)
    {
      fwrite([data bytes], 1, [data length], stdout);
      fputc('\n', stdout);
    }
}

- (NSDictionary *)versionPayload
{
  return [self payloadWithCommand: @"version"
                               ok: YES
                           status: @"ok"
                          summary: @"GNUstep CLI version"
                             data: [NSDictionary dictionaryWithObject: @"0.1.0-dev"
                                                              forKey: @"version"]];
}

- (NSString *)repositoryRoot
{
  NSString *binaryPath = [[[NSProcessInfo processInfo] arguments] objectAtIndex: 0];
  NSString *resolvedPath = [binaryPath stringByResolvingSymlinksInPath];
  NSString *candidate = [resolvedPath stringByDeletingLastPathComponent];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *scriptsPath = nil;

  while ([candidate length] > 1)
    {
      scriptsPath = [candidate stringByAppendingPathComponent: @"scripts/internal"];
      if ([manager fileExistsAtPath: scriptsPath])
        {
          return candidate;
        }
      candidate = [candidate stringByDeletingLastPathComponent];
    }

  candidate = [[manager currentDirectoryPath] stringByResolvingSymlinksInPath];
  while ([candidate length] > 1)
    {
      scriptsPath = [candidate stringByAppendingPathComponent: @"scripts/internal"];
      if ([manager fileExistsAtPath: scriptsPath])
        {
          return candidate;
        }
      candidate = [candidate stringByDeletingLastPathComponent];
    }

  return nil;
}

- (NSString *)scriptNameForCommand:(NSString *)command
{
  if ([command isEqualToString: @"doctor"])
    {
      return @"doctor.py";
    }
  if ([command isEqualToString: @"setup"])
    {
      return @"setup_plan.py";
    }
  if ([command isEqualToString: @"build"])
    {
      return @"build.py";
    }
  if ([command isEqualToString: @"run"])
    {
      return @"run.py";
    }
  if ([command isEqualToString: @"new"])
    {
      return @"new_project.py";
    }
  if ([command isEqualToString: @"install"])
    {
      return @"install_package.py";
    }
  if ([command isEqualToString: @"remove"])
    {
      return @"remove_package.py";
    }
  return nil;
}

- (BOOL)commandRunsByDefault:(NSString *)command
{
  return [command isEqualToString: @"build"] || [command isEqualToString: @"run"];
}

- (BOOL)commandNeedsManagedRoot:(NSString *)command
{
  return [command isEqualToString: @"install"] || [command isEqualToString: @"remove"];
}

- (NSString *)defaultManagedRoot
{
#if defined(_WIN32)
  return @"%LOCALAPPDATA%\\gnustep-cli";
#else
  NSString *home = NSHomeDirectory();
  return [home stringByAppendingPathComponent: @".local/share/gnustep-cli"];
#endif
}

- (BOOL)arguments:(NSArray *)arguments containOption:(NSString *)option
{
  return [arguments containsObject: option];
}

- (int)runScriptForContext:(GSCommandContext *)context
{
  NSString *root = [self repositoryRoot];
  NSString *userDirectory = [[NSFileManager defaultManager] currentDirectoryPath];
  NSString *scriptName = [self scriptNameForCommand: [context command]];
  NSMutableArray *taskArguments = [NSMutableArray array];
  NSTask *task = [[[NSTask alloc] init] autorelease];

  if (root == nil || scriptName == nil)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload:
                  [self payloadWithCommand: [context command]
                                       ok: NO
                                   status: @"error"
                                  summary: @"The full CLI backend script could not be resolved."
                                     data: nil]];
        }
      else
        {
          fprintf(stderr, "gnustep: backend script for '%s' could not be resolved\n", [[context command] UTF8String]);
        }
      return 5;
    }

  [taskArguments addObject: @"python3"];
  [taskArguments addObject: [[root stringByAppendingPathComponent: @"scripts/internal"] stringByAppendingPathComponent: scriptName]];
  if ([context jsonOutput])
    {
      [taskArguments addObject: @"--json"];
    }
  if ([context verbose])
    {
      [taskArguments addObject: @"--verbose"];
    }
  if ([context quiet])
    {
      [taskArguments addObject: @"--quiet"];
    }
  if ([context yes])
    {
      [taskArguments addObject: @"--yes"];
    }
  if ([self commandRunsByDefault: [context command]] &&
      [self arguments: [context commandArguments] containOption: @"--execute"] == NO)
    {
      [taskArguments addObject: @"--execute"];
    }
  if ([self commandNeedsManagedRoot: [context command]] &&
      [self arguments: [context commandArguments] containOption: @"--root"] == NO)
    {
      [taskArguments addObject: @"--root"];
      [taskArguments addObject: [self defaultManagedRoot]];
    }
  [taskArguments addObjectsFromArray: [context commandArguments]];

  [task setCurrentDirectoryPath: userDirectory];
  [task setLaunchPath: @"/usr/bin/env"];
  [task setArguments: taskArguments];
  [task setStandardOutput: [NSFileHandle fileHandleWithStandardOutput]];
  [task setStandardError: [NSFileHandle fileHandleWithStandardError]];
  [task launch];
  [task waitUntilExit];
  return [task terminationStatus];
}

- (int)runWithArguments:(NSArray<NSString *> *)arguments
{
  GSCommandContext *context = [GSCommandContext contextWithArguments: arguments];
  NSString *command = nil;

  if ([context usageError] != nil)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload:
                  [self payloadWithCommand: @"gnustep"
                                       ok: NO
                                   status: @"error"
                                  summary: [context usageError]
                                     data: nil]];
        }
      else
        {
          fprintf(stderr, "%s\n", [[context usageError] UTF8String]);
        }
      return 2;
    }

  if ([context showVersion] && [context command] == nil)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload: [self versionPayload]];
        }
      else
        {
          printf("0.1.0-dev\n");
        }
      return 0;
    }

  if ([context showHelp] && [context command] == nil)
    {
      [self printHelp];
      return 0;
    }

  if ([context command] == nil)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload:
                  [self payloadWithCommand: @"gnustep"
                                       ok: NO
                                   status: @"error"
                                  summary: @"No command was provided."
                                     data: nil]];
        }
      else
        {
          [self printHelp];
        }
      return 2;
    }

  command = [context command];
  if ([self isKnownCommand: command] == NO)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload:
                  [self payloadWithCommand: command
                                       ok: NO
                                   status: @"error"
                                  summary: @"Unknown command."
                                     data: nil]];
        }
      else
        {
          fprintf(stderr, "%s: unknown command\n", [command UTF8String]);
        }
      return 2;
    }

  if ([context showHelp])
    {
      [self printCommandHelp: command];
      return 0;
    }

  return [self runScriptForContext: context];
}

@end
