#import "GSCommandRunner.h"
#import "GSCommandContext.h"

#import <sys/stat.h>
#import <unistd.h>

@interface GSCommandRunner ()

- (BOOL)isKnownCommand:(NSString *)command;
- (NSString *)commandSummary:(NSString *)command;
- (void)printCommandHelp:(NSString *)command;
- (void)printHelp;
- (NSDictionary *)payloadWithCommand:(NSString *)command
                                  ok:(BOOL)ok
                              status:(NSString *)status
                             summary:(NSString *)summary
                                data:(NSDictionary *)data;
- (void)emitJSONPayload:(NSDictionary *)payload;
- (NSDictionary *)versionPayload;
- (NSString *)repositoryRoot;
- (NSString *)defaultManifestPath;
- (NSString *)defaultManagedRoot;
- (BOOL)arguments:(NSArray *)arguments containOption:(NSString *)option;
- (NSDictionary *)readJSONFile:(NSString *)path error:(NSString **)errorMessage;
- (BOOL)writeJSONStringObject:(id)object toPath:(NSString *)path error:(NSString **)errorMessage;
- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory;
- (NSString *)firstAvailableExecutable:(NSArray *)names;
- (NSDictionary *)checkWithID:(NSString *)checkID
                         title:(NSString *)title
                        status:(NSString *)status
                      severity:(NSString *)severity
                       message:(NSString *)message
                     interface:(NSString *)interface
                executionTier:(NSString *)executionTier
                       details:(NSDictionary *)details;
- (NSDictionary *)actionWithKind:(NSString *)kind
                         message:(NSString *)message
                        priority:(int)priority;
- (NSDictionary *)detectProjectAtPath:(NSString *)projectPath;
- (NSDictionary *)executeDoctorForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeSetupForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeBuildForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeRunForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeNewForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeInstallForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeRemoveForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (int)runNativeCommandForContext:(GSCommandContext *)context;

@end

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
  if ([command isEqualToString: @"doctor"])
    {
      printf("  gnustep doctor [--json] [--manifest <path>] [--interface bootstrap|full]\n\n");
    }
  else if ([command isEqualToString: @"setup"])
    {
      printf("  gnustep setup [--json] [--user|--system] [--root <path>] [--manifest <path>]\n\n");
    }
  else if ([command isEqualToString: @"build"])
    {
      printf("  gnustep build [--json] [project-dir]\n\n");
    }
  else if ([command isEqualToString: @"run"])
    {
      printf("  gnustep run [--json] [project-dir]\n\n");
    }
  else if ([command isEqualToString: @"new"])
    {
      printf("  gnustep new [--json] [--list-templates] <template> <destination> [--name <name>]\n\n");
    }
  else if ([command isEqualToString: @"install"])
    {
      printf("  gnustep install [--json] [--root <path>] <package-manifest>\n\n");
    }
  else if ([command isEqualToString: @"remove"])
    {
      printf("  gnustep remove [--json] [--root <path>] <package-id>\n\n");
    }
  else
    {
      printf("  gnustep %s [options]\n\n", [command UTF8String]);
    }
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
  NSError *error = nil;
  NSData *data = [NSJSONSerialization dataWithJSONObject: payload options: 0 error: &error];
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
  NSString *binaryDir = [resolvedPath stringByDeletingLastPathComponent];
  NSString *installRoot = [binaryDir stringByDeletingLastPathComponent];
  NSString *candidate = [resolvedPath stringByDeletingLastPathComponent];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *libexecRoot = [installRoot stringByAppendingPathComponent: @"libexec/gnustep-cli"];

  if ([manager fileExistsAtPath: [libexecRoot stringByAppendingPathComponent: @"examples"]])
    {
      return libexecRoot;
    }

  while ([candidate length] > 1)
    {
      if ([manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"examples"]] &&
          [manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"src/full-cli"]])
        {
          return candidate;
        }
      candidate = [candidate stringByDeletingLastPathComponent];
    }

  candidate = [[manager currentDirectoryPath] stringByResolvingSymlinksInPath];
  while ([candidate length] > 1)
    {
      if ([manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"examples"]] &&
          [manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"src/full-cli"]])
        {
          return candidate;
        }
      candidate = [candidate stringByDeletingLastPathComponent];
    }

  return nil;
}

- (NSString *)defaultManifestPath
{
  NSString *root = [self repositoryRoot];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *staged = nil;
  NSString *example = nil;

  if (root == nil)
    {
      return nil;
    }
  staged = [[root stringByAppendingPathComponent: @"dist/stable/0.1.0-dev"] stringByAppendingPathComponent: @"release-manifest.json"];
  if ([manager fileExistsAtPath: staged])
    {
      return staged;
    }
  example = [[root stringByAppendingPathComponent: @"examples"] stringByAppendingPathComponent: @"release-manifest-v1.json"];
  if ([manager fileExistsAtPath: example])
    {
      return example;
    }
  return nil;
}

- (NSString *)defaultManagedRoot
{
#if defined(_WIN32)
  return @"%LOCALAPPDATA%\\gnustep-cli";
#else
  return [NSHomeDirectory() stringByAppendingPathComponent: @".local/share/gnustep-cli"];
#endif
}

- (BOOL)arguments:(NSArray *)arguments containOption:(NSString *)option
{
  return [arguments containsObject: option];
}

- (NSDictionary *)readJSONFile:(NSString *)path error:(NSString **)errorMessage
{
  NSData *data = [NSData dataWithContentsOfFile: path];
  NSError *error = nil;
  id object = nil;

  if (data == nil)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Could not read JSON file at %@", path];
        }
      return nil;
    }

  object = [NSJSONSerialization JSONObjectWithData: data options: 0 error: &error];
  if (object == nil || [object isKindOfClass: [NSDictionary class]] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Invalid JSON in %@", path];
        }
      return nil;
    }
  return (NSDictionary *)object;
}

- (BOOL)writeJSONStringObject:(id)object toPath:(NSString *)path error:(NSString **)errorMessage
{
  NSError *error = nil;
  NSData *data = [NSJSONSerialization dataWithJSONObject: object
                                                 options: NSJSONWritingPrettyPrinted
                                                   error: &error];
  if (data == nil)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Failed to encode JSON output.";
        }
      return NO;
    }
  if ([data writeToFile: path atomically: YES] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Failed to write %@", path];
        }
      return NO;
    }
  return YES;
}

- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory
{
  NSTask *task = [[[NSTask alloc] init] autorelease];
  NSPipe *stdoutPipe = [NSPipe pipe];
  NSPipe *stderrPipe = [NSPipe pipe];
  NSData *stdoutData = nil;
  NSData *stderrData = nil;
  NSString *stdoutString = @"";
  NSString *stderrString = @"";

  [task setLaunchPath: @"/usr/bin/env"];
  [task setArguments: arguments];
  if (currentDirectory != nil)
    {
      [task setCurrentDirectoryPath: currentDirectory];
    }
  [task setStandardOutput: stdoutPipe];
  [task setStandardError: stderrPipe];

  @try
    {
      [task launch];
      [task waitUntilExit];
    }
  @catch (NSException *exception)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            @"", @"stdout",
                            [exception reason], @"stderr",
                            nil];
    }

  stdoutData = [[stdoutPipe fileHandleForReading] readDataToEndOfFile];
  stderrData = [[stderrPipe fileHandleForReading] readDataToEndOfFile];
  if (stdoutData != nil && [stdoutData length] > 0)
    {
      stdoutString = [[[NSString alloc] initWithData: stdoutData encoding: NSUTF8StringEncoding] autorelease];
      if (stdoutString == nil)
        {
          stdoutString = @"";
        }
    }
  if (stderrData != nil && [stderrData length] > 0)
    {
      stderrString = [[[NSString alloc] initWithData: stderrData encoding: NSUTF8StringEncoding] autorelease];
      if (stderrString == nil)
        {
          stderrString = @"";
        }
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: YES], @"launched",
                        [NSNumber numberWithInt: [task terminationStatus]], @"exit_status",
                        stdoutString, @"stdout",
                        stderrString, @"stderr",
                        nil];
}

- (NSDictionary *)checkWithID:(NSString *)checkID
                         title:(NSString *)title
                        status:(NSString *)status
                      severity:(NSString *)severity
                       message:(NSString *)message
                     interface:(NSString *)interface
                executionTier:(NSString *)executionTier
                       details:(NSDictionary *)details
{
  NSMutableDictionary *payload = [NSMutableDictionary dictionaryWithObjectsAndKeys:
                                                       checkID, @"id",
                                                       title, @"title",
                                                       status, @"status",
                                                       severity, @"severity",
                                                       message, @"message",
                                                       nil];
  if (interface != nil)
    {
      [payload setObject: interface forKey: @"interface"];
    }
  if (executionTier != nil)
    {
      [payload setObject: executionTier forKey: @"execution_tier"];
    }
  if (details != nil && [details count] > 0)
    {
      [payload setObject: details forKey: @"details"];
    }
  return payload;
}

- (NSDictionary *)actionWithKind:(NSString *)kind
                         message:(NSString *)message
                        priority:(int)priority
{
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        kind, @"kind",
                        [NSNumber numberWithInt: priority], @"priority",
                        message, @"message",
                        nil];
}

- (NSString *)firstAvailableExecutable:(NSArray *)names
{
  NSUInteger i = 0;
  NSFileManager *manager = [NSFileManager defaultManager];
  NSArray *pathEntries = [[[NSProcessInfo processInfo] environment] objectForKey: @"PATH"] ?
    [[[[NSProcessInfo processInfo] environment] objectForKey: @"PATH"] componentsSeparatedByString: @":"] :
    [NSArray array];

  for (i = 0; i < [names count]; i++)
    {
      NSString *name = [names objectAtIndex: i];
      NSUInteger j = 0;
      for (j = 0; j < [pathEntries count]; j++)
        {
          NSString *candidate = [[pathEntries objectAtIndex: j] stringByAppendingPathComponent: name];
          if ([manager isExecutableFileAtPath: candidate])
            {
              return candidate;
            }
        }
    }
  return nil;
}

- (NSDictionary *)parseGNUmakefile:(NSString *)path
{
  NSString *content = [NSString stringWithContentsOfFile: path
                                                encoding: NSUTF8StringEncoding
                                                   error: nil];
  NSMutableDictionary *values = [NSMutableDictionary dictionary];
  NSArray *lines = nil;
  NSUInteger i = 0;

  if (content == nil)
    {
      return values;
    }
  lines = [content componentsSeparatedByString: @"\n"];
  for (i = 0; i < [lines count]; i++)
    {
      NSString *line = [[lines objectAtIndex: i] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
      NSRange range = NSMakeRange(NSNotFound, 0);
      NSString *key = nil;
      NSString *value = nil;

      if ([line length] == 0 || [line hasPrefix: @"#"])
        {
          continue;
        }
      range = [line rangeOfString: @"="];
      if (range.location == NSNotFound)
        {
          continue;
        }
      key = [[line substringToIndex: range.location] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
      value = [[line substringFromIndex: range.location + 1] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
      if (key != nil && value != nil)
        {
          [values setObject: value forKey: key];
        }
    }
  return values;
}

- (NSDictionary *)detectProjectAtPath:(NSString *)projectPath
{
  NSString *root = [projectPath stringByResolvingSymlinksInPath];
  NSString *gnumakefile = [root stringByAppendingPathComponent: @"GNUmakefile"];
  NSDictionary *values = nil;
  NSString *projectType = nil;
  NSString *targetName = nil;

  if ([[NSFileManager defaultManager] fileExistsAtPath: gnumakefile] == NO)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"supported",
                            @"missing_gnumakefile", @"reason",
                            root, @"project_dir",
                            nil];
    }

  values = [self parseGNUmakefile: gnumakefile];
  targetName = [values objectForKey: @"TOOL_NAME"];
  if (targetName != nil)
    {
      projectType = @"tool";
    }
  else
    {
      targetName = [values objectForKey: @"APP_NAME"];
      if (targetName != nil)
        {
          projectType = @"app";
        }
      else
        {
          targetName = [values objectForKey: @"LIBRARY_NAME"];
          if (targetName != nil)
            {
              projectType = @"library";
            }
        }
    }

  if (projectType == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"supported",
                            @"unsupported_gnumakefile", @"reason",
                            root, @"project_dir",
                            gnumakefile, @"gnumakefile",
                            nil];
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: YES], @"supported",
                        root, @"project_dir",
                        gnumakefile, @"gnumakefile",
                        projectType, @"project_type",
                        targetName, @"target_name",
                        nil];
}

- (NSString *)sha256ForFile:(NSString *)path
{
  NSArray *commands = [NSArray arrayWithObjects:
                                 [NSArray arrayWithObjects: @"sha256sum", path, nil],
                                 [NSArray arrayWithObjects: @"shasum", @"-a", @"256", path, nil],
                                 [NSArray arrayWithObjects: @"openssl", @"dgst", @"-sha256", path, nil],
                                 nil];
  NSUInteger i = 0;

  for (i = 0; i < [commands count]; i++)
    {
      NSDictionary *result = [self runCommand: [commands objectAtIndex: i] currentDirectory: nil];
      if ([[result objectForKey: @"launched"] boolValue] &&
          [[result objectForKey: @"exit_status"] intValue] == 0)
        {
          NSString *output = [[result objectForKey: @"stdout"] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
          NSArray *parts = [output componentsSeparatedByCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
          NSUInteger j = 0;
          for (j = 0; j < [parts count]; j++)
            {
              NSString *part = [parts objectAtIndex: j];
              if ([part length] == 64)
                {
                  return part;
                }
            }
        }
    }
  return nil;
}

- (BOOL)extractArchive:(NSString *)archivePath toDirectory:(NSString *)destination error:(NSString **)errorMessage
{
  NSDictionary *result = nil;
  NSFileManager *manager = [NSFileManager defaultManager];

  [manager createDirectoryAtPath: destination withIntermediateDirectories: YES attributes: nil error: nil];
  if ([[archivePath lowercaseString] hasSuffix: @".zip"])
    {
      result = [self runCommand: [NSArray arrayWithObjects: @"unzip", @"-q", archivePath, @"-d", destination, nil]
               currentDirectory: nil];
    }
  else
    {
      result = [self runCommand: [NSArray arrayWithObjects: @"tar", @"-xzf", archivePath, @"-C", destination, nil]
               currentDirectory: nil];
    }

  if ([[result objectForKey: @"launched"] boolValue] == NO ||
      [[result objectForKey: @"exit_status"] intValue] != 0)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [result objectForKey: @"stderr"];
        }
      return NO;
    }
  return YES;
}

- (NSString *)singleChildDirectoryOrSelf:(NSString *)path
{
  NSArray *children = [[NSFileManager defaultManager] contentsOfDirectoryAtPath: path error: nil];
  if ([children count] == 1)
    {
      NSString *child = [path stringByAppendingPathComponent: [children objectAtIndex: 0]];
      BOOL isDir = NO;
      if ([[NSFileManager defaultManager] fileExistsAtPath: child isDirectory: &isDir] && isDir)
        {
          return child;
        }
    }
  return path;
}

- (BOOL)copyTreeContentsFrom:(NSString *)source to:(NSString *)destination error:(NSString **)errorMessage
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDirectoryEnumerator *enumerator = nil;
  NSString *relative = nil;

  [manager createDirectoryAtPath: destination withIntermediateDirectories: YES attributes: nil error: nil];
  enumerator = [manager enumeratorAtPath: source];
  while ((relative = [enumerator nextObject]) != nil)
    {
      NSString *sourcePath = [source stringByAppendingPathComponent: relative];
      NSString *targetPath = [destination stringByAppendingPathComponent: relative];
      BOOL isDir = NO;

      [manager fileExistsAtPath: sourcePath isDirectory: &isDir];
      if (isDir)
        {
          [manager createDirectoryAtPath: targetPath withIntermediateDirectories: YES attributes: nil error: nil];
        }
      else
        {
          [manager createDirectoryAtPath: [targetPath stringByDeletingLastPathComponent]
             withIntermediateDirectories: YES
                              attributes: nil
                                   error: nil];
          [manager removeItemAtPath: targetPath error: nil];
          if ([manager copyItemAtPath: sourcePath toPath: targetPath error: nil] == NO)
            {
              if (errorMessage != NULL)
                {
                  *errorMessage = [NSString stringWithFormat: @"Failed to copy %@", relative];
                }
              return NO;
            }
        }
    }
  return YES;
}

- (NSDictionary *)validateAndLoadManifest:(NSString *)manifestPath error:(NSString **)errorMessage
{
  NSDictionary *manifest = [self readJSONFile: manifestPath error: errorMessage];
  NSArray *releases = nil;

  if (manifest == nil)
    {
      return nil;
    }
  if ([[manifest objectForKey: @"schema_version"] intValue] != 1)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Unsupported release manifest schema version.";
        }
      return nil;
    }
  releases = [manifest objectForKey: @"releases"];
  if ([releases isKindOfClass: [NSArray class]] == NO || [releases count] == 0)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Release manifest does not define any releases.";
        }
      return nil;
    }
  return manifest;
}

- (NSDictionary *)selectReleaseFromManifest:(NSDictionary *)manifest
{
  NSArray *releases = [manifest objectForKey: @"releases"];
  NSUInteger i = 0;
  for (i = 0; i < [releases count]; i++)
    {
      NSDictionary *release = [releases objectAtIndex: i];
      if ([[release objectForKey: @"status"] isEqualToString: @"active"])
        {
          return release;
        }
    }
  return [releases objectAtIndex: 0];
}

- (NSArray *)selectedArtifactsForRelease:(NSDictionary *)release os:(NSString *)osName arch:(NSString *)arch
{
  NSArray *artifacts = [release objectForKey: @"artifacts"];
  NSMutableDictionary *selectedByKind = [NSMutableDictionary dictionary];
  NSMutableArray *ordered = [NSMutableArray array];
  NSUInteger i = 0;
  NSArray *order = [NSArray arrayWithObjects: @"cli", @"toolchain", nil];

  for (i = 0; i < [artifacts count]; i++)
    {
      NSDictionary *artifact = [artifacts objectAtIndex: i];
      if ([[artifact objectForKey: @"os"] isEqualToString: osName] &&
          [[artifact objectForKey: @"arch"] isEqualToString: arch] &&
          [selectedByKind objectForKey: [artifact objectForKey: @"kind"]] == nil)
        {
          [selectedByKind setObject: artifact forKey: [artifact objectForKey: @"kind"]];
        }
    }

  for (i = 0; i < [order count]; i++)
    {
      NSDictionary *artifact = [selectedByKind objectForKey: [order objectAtIndex: i]];
      if (artifact != nil)
        {
          [ordered addObject: artifact];
        }
    }
  return ordered;
}

- (NSString *)normalizeOSName
{
  NSString *osName = [[NSProcessInfo processInfo] operatingSystemVersionString];
#if defined(_WIN32)
  return @"windows";
#else
  NSDictionary *env = [[NSProcessInfo processInfo] environment];
  NSString *ostype = [env objectForKey: @"OSTYPE"];
  if (ostype != nil && [ostype rangeOfString: @"openbsd"].location != NSNotFound)
    {
      return @"openbsd";
    }
  if ([osName rangeOfString: @"Linux"].location != NSNotFound ||
      [[NSFileManager defaultManager] fileExistsAtPath: @"/etc/os-release"])
    {
      return @"linux";
    }
  return @"unknown";
#endif
}

- (NSString *)normalizeArchName
{
  NSString *arch = nil;
  NSDictionary *result = [self runCommand: [NSArray arrayWithObjects: @"uname", @"-m", nil] currentDirectory: nil];
  arch = [[[result objectForKey: @"stdout"] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]] lowercaseString];
  if ([arch isEqualToString: @"x86_64"] || [arch isEqualToString: @"amd64"])
    {
      return @"amd64";
    }
  if ([arch isEqualToString: @"aarch64"] || [arch isEqualToString: @"arm64"])
    {
      return @"arm64";
    }
  return [arch length] > 0 ? arch : @"unknown";
}

- (NSDictionary *)compilerInfo
{
  NSString *compilerPath = [self firstAvailableExecutable: [NSArray arrayWithObjects: @"clang", @"gcc", @"cc", nil]];
  NSString *compilerFamily = nil;
  NSString *compilerVersion = nil;
  NSString *firstLine = @"";
  NSDictionary *result = nil;
  NSArray *parts = nil;
  NSUInteger i = 0;

  if (compilerPath == nil)
    {
      return [NSDictionary dictionary];
    }

  result = [self runCommand: [NSArray arrayWithObjects: compilerPath, @"--version", nil] currentDirectory: nil];
  if ([[result objectForKey: @"launched"] boolValue])
    {
      NSArray *lines = [[result objectForKey: @"stdout"] length] > 0 ?
        [[result objectForKey: @"stdout"] componentsSeparatedByString: @"\n"] :
        [[result objectForKey: @"stderr"] componentsSeparatedByString: @"\n"];
      if ([lines count] > 0)
        {
          firstLine = [lines objectAtIndex: 0];
        }
    }

  if ([[firstLine lowercaseString] rangeOfString: @"clang"].location != NSNotFound ||
      [[compilerPath lastPathComponent] rangeOfString: @"clang"].location != NSNotFound)
    {
      compilerFamily = @"clang";
    }
  else
    {
      compilerFamily = @"gcc";
    }

  parts = [[firstLine stringByReplacingOccurrencesOfString: @"(" withString: @" "]
              componentsSeparatedByString: @" "];
  for (i = 0; i < [parts count]; i++)
    {
      NSString *part = [parts objectAtIndex: i];
      if ([part length] > 0 && [[NSCharacterSet decimalDigitCharacterSet] characterIsMember: [part characterAtIndex: 0]])
        {
          compilerVersion = part;
          break;
        }
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        compilerPath, @"path",
                        compilerFamily, @"family",
                        compilerVersion ? compilerVersion : @"unknown", @"version",
                        nil];
}

- (NSDictionary *)probeCompiler:(NSString *)compilerPath
{
  NSString *tempDir = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *source = [tempDir stringByAppendingPathComponent: @"probe.m"];
  NSString *object = [tempDir stringByAppendingPathComponent: @"probe.o"];
  NSString *binary = [tempDir stringByAppendingPathComponent: @"probe"];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDictionary *compileResult = nil;
  NSDictionary *linkResult = nil;
  NSDictionary *runResult = nil;
  BOOL canCompile = NO;
  BOOL canLink = NO;
  BOOL canRun = NO;

  if (compilerPath == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"can_compile",
                            [NSNumber numberWithBool: NO], @"can_link",
                            [NSNumber numberWithBool: NO], @"can_run",
                            nil];
    }

  [manager createDirectoryAtPath: tempDir withIntermediateDirectories: YES attributes: nil error: nil];
  [@"int main(void) { return 0; }\n" writeToFile: source atomically: YES encoding: NSUTF8StringEncoding error: nil];

  compileResult = [self runCommand: [NSArray arrayWithObjects: compilerPath, @"-x", @"objective-c", @"-c", source, @"-o", object, nil]
                  currentDirectory: nil];
  canCompile = [[compileResult objectForKey: @"exit_status"] intValue] == 0 && [manager fileExistsAtPath: object];
  if (canCompile)
    {
      linkResult = [self runCommand: [NSArray arrayWithObjects: compilerPath, object, @"-o", binary, nil] currentDirectory: nil];
      canLink = [[linkResult objectForKey: @"exit_status"] intValue] == 0 && [manager fileExistsAtPath: binary];
    }
  if (canLink)
    {
      runResult = [self runCommand: [NSArray arrayWithObjects: binary, nil] currentDirectory: nil];
      canRun = [[runResult objectForKey: @"exit_status"] intValue] == 0;
    }

  [manager removeItemAtPath: tempDir error: nil];
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: canCompile], @"can_compile",
                        [NSNumber numberWithBool: canLink], @"can_link",
                        [NSNumber numberWithBool: canRun], @"can_run",
                        nil];
}

- (NSDictionary *)toolchainFacts
{
  NSString *gnustepConfig = [self firstAvailableExecutable: [NSArray arrayWithObjects: @"gnustep-config", nil]];
  NSString *gnustepMakefiles = [[[NSProcessInfo processInfo] environment] objectForKey: @"GNUSTEP_MAKEFILES"];
  NSDictionary *compiler = [self compilerInfo];
  NSDictionary *probe = [self probeCompiler: [compiler objectForKey: @"path"]];
  NSString *compilerFamily = [compiler objectForKey: @"family"];
  BOOL present = (gnustepConfig != nil || gnustepMakefiles != nil);
  NSMutableDictionary *featureFlags = [NSMutableDictionary dictionaryWithObjectsAndKeys:
                                                              [NSNumber numberWithBool: NO], @"objc2_syntax",
                                                              [NSNumber numberWithBool: NO], @"blocks",
                                                              [NSNumber numberWithBool: NO], @"arc",
                                                              [NSNumber numberWithBool: NO], @"nonfragile_abi",
                                                              [NSNumber numberWithBool: NO], @"associated_objects",
                                                              [NSNumber numberWithBool: YES], @"exceptions",
                                                              nil];
  NSString *objcRuntime = @"unknown";
  NSString *objcABI = @"unknown";

  if ([compilerFamily isEqualToString: @"clang"])
    {
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"objc2_syntax"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"blocks"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"arc"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"nonfragile_abi"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"associated_objects"];
      objcRuntime = present ? @"libobjc2" : @"unknown";
      objcABI = present ? @"modern" : @"unknown";
    }
  else if ([compilerFamily isEqualToString: @"gcc"])
    {
      objcRuntime = present ? @"gcc_libobjc" : @"unknown";
      objcABI = present ? @"legacy" : @"unknown";
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: present], @"present",
                        compilerFamily ? compilerFamily : @"unknown", @"compiler_family",
                        [compiler objectForKey: @"version"] ? [compiler objectForKey: @"version"] : @"unknown", @"compiler_version",
                        compilerFamily ? compilerFamily : @"unknown", @"toolchain_flavor",
                        objcRuntime, @"objc_runtime",
                        objcABI, @"objc_abi",
                        [NSNumber numberWithBool: (gnustepConfig != nil || gnustepMakefiles != nil)], @"gnustep_make",
                        [NSNumber numberWithBool: NO], @"gnustep_base",
                        [NSNumber numberWithBool: NO], @"gnustep_gui",
                        [probe objectForKey: @"can_compile"], @"can_compile",
                        [probe objectForKey: @"can_link"], @"can_link",
                        [probe objectForKey: @"can_run"], @"can_run",
                        featureFlags, @"feature_flags",
                        gnustepConfig ? gnustepConfig : [NSNull null], @"gnustep_config_path",
                        gnustepMakefiles ? gnustepMakefiles : [NSNull null], @"gnustep_makefiles",
                        nil];
}

- (NSDictionary *)evaluateCompatibilityForEnvironment:(NSDictionary *)environment artifact:(NSDictionary *)artifact
{
  NSMutableArray *reasons = [NSMutableArray array];
  NSMutableArray *warnings = [NSMutableArray array];
  NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
  NSString *detectedCompiler = [toolchain objectForKey: @"compiler_family"];
  NSDictionary *featureFlags = [toolchain objectForKey: @"feature_flags"];
  NSArray *requiredFeatures = artifact ? [artifact objectForKey: @"required_features"] : nil;
  NSUInteger i = 0;

  if (artifact == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"compatible",
                            [NSNull null], @"target_kind",
                            [NSNull null], @"target_id",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"unsupported_os", @"code",
                                                     @"No managed artifact matched the detected operating system and architecture.", @"message",
                                                     nil]], @"reasons",
                            [NSArray array], @"warnings",
                            nil];
    }

  if ([[environment objectForKey: @"os"] isEqualToString: [artifact objectForKey: @"os"]] == NO)
    {
      [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"unsupported_os", @"code",
                                           @"Detected OS does not match the selected artifact OS.", @"message",
                                           nil]];
    }
  if ([[environment objectForKey: @"arch"] isEqualToString: [artifact objectForKey: @"arch"]] == NO)
    {
      [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"unsupported_arch", @"code",
                                           @"Detected architecture does not match the selected artifact architecture.", @"message",
                                           nil]];
    }
  if ([[toolchain objectForKey: @"present"] boolValue])
    {
      if (detectedCompiler != nil &&
          [detectedCompiler isEqualToString: [artifact objectForKey: @"compiler_family"]] == NO)
        {
          [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               @"compiler_family_mismatch", @"code",
                                               [NSString stringWithFormat: @"Detected compiler family is %@, but the selected managed artifact requires %@.",
                                                 detectedCompiler,
                                                 [artifact objectForKey: @"compiler_family"]], @"message",
                                               nil]];
        }
      for (i = 0; i < [requiredFeatures count]; i++)
        {
          NSString *feature = [requiredFeatures objectAtIndex: i];
          if ([[featureFlags objectForKey: feature] boolValue] == NO)
            {
              [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"missing_required_feature", @"code",
                                                   [NSString stringWithFormat: @"The detected toolchain does not support required feature '%@'.", feature], @"message",
                                                   nil]];
            }
        }
      if ([detectedCompiler isEqualToString: @"gcc"])
        {
          [warnings addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                @"gcc_toolchain_detected", @"code",
                                                @"A GCC-based GNUstep environment is installed. Some modern Objective-C features require a Clang-based toolchain.", @"message",
                                                nil]];
        }
    }
  else
    {
      [warnings addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                            @"toolchain_not_present", @"code",
                                            @"No preexisting GNUstep toolchain was detected; a managed install will be required.", @"message",
                                            nil]];
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: ([reasons count] == 0)], @"compatible",
                        [artifact objectForKey: @"kind"], @"target_kind",
                        [artifact objectForKey: @"id"], @"target_id",
                        reasons, @"reasons",
                        warnings, @"warnings",
                        nil];
}

- (NSString *)classifyEnvironment:(NSDictionary *)environment compatibility:(NSDictionary *)compatibility
{
  NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
  if ([[toolchain objectForKey: @"present"] boolValue] == NO)
    {
      return @"no_toolchain";
    }
  if ([[toolchain objectForKey: @"can_compile"] boolValue] == NO ||
      [[toolchain objectForKey: @"can_link"] boolValue] == NO ||
      [[toolchain objectForKey: @"can_run"] boolValue] == NO)
    {
      return @"toolchain_broken";
    }
  if ([[compatibility objectForKey: @"compatible"] boolValue] == NO)
    {
      return @"toolchain_incompatible";
    }
  return @"toolchain_compatible";
}

- (NSDictionary *)buildDoctorPayloadWithInterface:(NSString *)interface manifestPath:(NSString *)manifestPath
{
  NSString *osName = [self normalizeOSName];
  NSString *arch = [self normalizeArchName];
  NSDictionary *toolchain = [self toolchainFacts];
  NSMutableDictionary *environment = [NSMutableDictionary dictionary];
  NSDictionary *manifest = nil;
  NSDictionary *release = nil;
  NSDictionary *artifact = nil;
  NSDictionary *compatibility = nil;
  NSString *classification = nil;
  NSString *status = @"ok";
  NSMutableArray *checks = [NSMutableArray array];
  NSMutableArray *actions = [NSMutableArray array];
  NSString *summary = nil;
  NSString *manifestError = nil;

  [environment setObject: osName forKey: @"os"];
  [environment setObject: arch forKey: @"arch"];
  [environment setObject: @"posix" forKey: @"shell_family"];
  [environment setObject: @"user" forKey: @"install_scope"];
  [environment setObject: toolchain forKey: @"toolchain"];
  [environment setObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                          [NSNumber numberWithBool: ([self firstAvailableExecutable: [NSArray arrayWithObjects: @"curl", nil]] != nil)], @"curl",
                                          [NSNumber numberWithBool: ([self firstAvailableExecutable: [NSArray arrayWithObjects: @"wget", nil]] != nil)], @"wget",
                                          nil]
                 forKey: @"bootstrap_prerequisites"];
  [environment setObject: [NSArray array] forKey: @"detected_layouts"];
  [environment setObject: [NSArray array] forKey: @"install_prefixes"];

  if (manifestPath != nil)
    {
      manifest = [self validateAndLoadManifest: manifestPath error: &manifestError];
      if (manifest != nil)
        {
          NSArray *selected = nil;
          NSUInteger i = 0;
          release = [self selectReleaseFromManifest: manifest];
          selected = [self selectedArtifactsForRelease: release os: osName arch: arch];
          for (i = 0; i < [selected count]; i++)
            {
              NSDictionary *candidate = [selected objectAtIndex: i];
              if ([[candidate objectForKey: @"kind"] isEqualToString: @"toolchain"])
                {
                  artifact = candidate;
                  break;
                }
            }
        }
    }

  compatibility = [self evaluateCompatibilityForEnvironment: environment artifact: artifact];
  classification = [self classifyEnvironment: environment compatibility: compatibility];

  if ([classification isEqualToString: @"toolchain_incompatible"] ||
      [classification isEqualToString: @"toolchain_broken"])
    {
      status = @"error";
    }
  else if ([classification isEqualToString: @"no_toolchain"])
    {
      status = @"warning";
    }

  [checks addObject: [self checkWithID: @"host.identity"
                                 title: @"Determine host identity"
                                status: @"ok"
                              severity: @"info"
                               message: [NSString stringWithFormat: @"Detected %@ on %@.", osName, arch]
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_required"
                               details: nil]];
  [checks addObject: [self checkWithID: @"bootstrap.downloader"
                                 title: @"Check for downloader"
                                status: ([[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"curl"] boolValue] ||
                                         [[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"wget"] boolValue]) ? @"ok" : @"error"
                              severity: @"error"
                               message: ([[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"curl"] boolValue] ||
                                         [[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"wget"] boolValue]) ? @"Found curl or wget." : @"Neither curl nor wget is available."
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_required"
                               details: nil]];
  [checks addObject: [self checkWithID: @"toolchain.detect"
                                 title: @"Detect GNUstep toolchain"
                                status: [[toolchain objectForKey: @"present"] boolValue] ? @"ok" : @"warning"
                              severity: @"error"
                               message: [[toolchain objectForKey: @"present"] boolValue] ?
                                 [NSString stringWithFormat: @"Detected a %@-based GNUstep toolchain.", [toolchain objectForKey: @"compiler_family"]] :
                                 @"No GNUstep toolchain detected."
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_optional"
                               details: nil]];

  if ([interface isEqualToString: @"full"])
    {
      [checks addObject: [self checkWithID: @"toolchain.probe"
                                     title: @"Compile/link/run probe"
                                    status: ([[toolchain objectForKey: @"can_compile"] boolValue] &&
                                             [[toolchain objectForKey: @"can_link"] boolValue] &&
                                             [[toolchain objectForKey: @"can_run"] boolValue]) ? @"ok" : @"warning"
                                  severity: @"error"
                                   message: ([[toolchain objectForKey: @"can_compile"] boolValue] &&
                                             [[toolchain objectForKey: @"can_link"] boolValue] &&
                                             [[toolchain objectForKey: @"can_run"] boolValue]) ?
                                     @"The compiler can compile, link, and run a minimal Objective-C probe." :
                                     @"A compiler probe did not fully succeed."
                                 interface: @"full"
                            executionTier: @"full_only"
                                   details: nil]];
    }
  else
    {
      [checks addObject: [self checkWithID: @"toolchain.probe"
                                     title: @"Compile/link/run probe"
                                    status: @"not_run"
                                  severity: @"error"
                                   message: @"This check is available in the full CLI only."
                                 interface: @"full"
                            executionTier: @"full_only"
                                   details: [NSDictionary dictionaryWithObject: [NSNumber numberWithBool: YES]
                                                                        forKey: @"unavailable_in_bootstrap"]]];
    }

  [checks addObject: [self checkWithID: @"toolchain.compatibility"
                                 title: @"Evaluate managed artifact compatibility"
                                status: artifact ? ([[compatibility objectForKey: @"compatible"] boolValue] ? @"ok" : @"error") : @"warning"
                              severity: @"error"
                               message: artifact ?
                                 ([[compatibility objectForKey: @"compatible"] boolValue] ?
                                  [NSString stringWithFormat: @"The environment is compatible with artifact %@.", [artifact objectForKey: @"id"]] :
                                  [NSString stringWithFormat: @"The environment is not compatible with artifact %@.", [artifact objectForKey: @"id"]]) :
                                 @"No matching managed artifact was found for this host."
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_optional"
                               details: nil]];

  if ([[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"curl"] boolValue] == NO &&
      [[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"wget"] boolValue] == NO)
    {
      [actions addObject: [self actionWithKind: @"install_downloader"
                                       message: @"Install curl or wget, then rerun setup."
                                      priority: 1]];
    }
  if ([classification isEqualToString: @"no_toolchain"])
    {
      [actions addObject: [self actionWithKind: @"install_managed_toolchain"
                                       message: @"Install the supported managed GNUstep toolchain."
                                      priority: 1]];
    }
  else if ([classification isEqualToString: @"toolchain_incompatible"])
    {
      [actions addObject: [self actionWithKind: @"install_managed_toolchain"
                                       message: @"Install the supported Clang-based managed toolchain."
                                      priority: 1]];
    }
  else if ([classification isEqualToString: @"toolchain_broken"])
    {
      [actions addObject: [self actionWithKind: @"repair_or_replace_toolchain"
                                       message: @"Repair the detected toolchain or install a managed one."
                                      priority: 1]];
    }
  else
    {
      [actions addObject: [self actionWithKind: @"use_existing_toolchain"
                                       message: @"You can continue with the detected toolchain or install a managed one explicitly."
                                      priority: 1]];
    }

  if ([classification isEqualToString: @"no_toolchain"])
    {
      summary = @"No preexisting GNUstep toolchain was detected.";
    }
  else if ([classification isEqualToString: @"toolchain_compatible"])
    {
      summary = @"A compatible GNUstep toolchain was detected.";
    }
  else if ([classification isEqualToString: @"toolchain_incompatible"])
    {
      summary = @"A GNUstep toolchain was detected, but it is incompatible with the selected managed artifacts.";
    }
  else
    {
      summary = @"A GNUstep toolchain was detected, but it does not appear to be working correctly.";
    }

  if (manifestError != nil && artifact == nil)
    {
      compatibility = [NSDictionary dictionaryWithObjectsAndKeys:
                                       [NSNumber numberWithBool: NO], @"compatible",
                                       [NSNull null], @"target_kind",
                                       [NSNull null], @"target_id",
                                       [NSArray arrayWithObject:
                                                [NSDictionary dictionaryWithObjectsAndKeys:
                                                                @"manifest_invalid", @"code",
                                                                manifestError, @"message",
                                                                nil]], @"reasons",
                                       [NSArray array], @"warnings",
                                       nil];
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"doctor", @"command",
                        @"0.1.0-dev", @"cli_version",
                        interface, @"interface",
                        [interface isEqualToString: @"bootstrap"] ? @"installer" : @"full", @"diagnostic_depth",
                        [NSNumber numberWithBool: ![status isEqualToString: @"error"]], @"ok",
                        status, @"status",
                        classification, @"environment_classification",
                        summary, @"summary",
                        environment, @"environment",
                        compatibility, @"compatibility",
                        checks, @"checks",
                        actions, @"actions",
                        nil];
}

- (NSDictionary *)executeDoctorForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *manifestPath = nil;
  NSString *interface = @"full";
  NSUInteger i = 0;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--manifest"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: @"--manifest requires a value." data: nil];
            }
          manifestPath = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--interface"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: @"--interface requires a value." data: nil];
            }
          interface = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown doctor option: %@", argument] data: nil];
        }
    }

  if (manifestPath == nil)
    {
      manifestPath = [self defaultManifestPath];
    }
  if (manifestPath == nil)
    {
      *exitCode = 5;
      return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: @"No release manifest could be resolved." data: nil];
    }

  {
    NSDictionary *payload = [self buildDoctorPayloadWithInterface: interface manifestPath: manifestPath];
    *exitCode = [[payload objectForKey: @"ok"] boolValue] ? 0 : 3;
    return payload;
  }
}

- (NSDictionary *)buildSetupPayloadForScope:(NSString *)scope
                                 manifest:(NSString *)manifestPath
                               installRoot:(NSString *)installRoot
                                  execute:(BOOL)execute
                                  exitCode:(int *)exitCode
{
  NSString *resolvedManifest = manifestPath ? manifestPath : [self defaultManifestPath];
  NSDictionary *doctor = nil;
  NSDictionary *manifest = nil;
  NSDictionary *release = nil;
  NSArray *selectedArtifacts = nil;
  NSString *osName = [self normalizeOSName];
  NSString *selectedRoot = installRoot ? installRoot : ([scope isEqualToString: @"system"] ? @"/opt/gnustep-cli" : [self defaultManagedRoot]);
  NSMutableArray *actions = [NSMutableArray array];
  NSString *summary = @"Managed installation plan created.";
  NSString *status = @"ok";
  BOOL ok = YES;
  NSString *errorMessage = nil;
  BOOL isRoot = (geteuid() == 0);
  BOOL rootWritable = YES;

  if (resolvedManifest == nil)
    {
      *exitCode = 5;
      return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"No release manifest could be resolved." data: nil];
    }

  doctor = [self buildDoctorPayloadWithInterface: @"bootstrap" manifestPath: resolvedManifest];
  manifest = [self validateAndLoadManifest: resolvedManifest error: &errorMessage];
  if (manifest != nil)
    {
      release = [self selectReleaseFromManifest: manifest];
      selectedArtifacts = [self selectedArtifactsForRelease: release
                                                         os: [[doctor objectForKey: @"environment"] objectForKey: @"os"]
                                                       arch: [[doctor objectForKey: @"environment"] objectForKey: @"arch"]];
    }
  else
    {
      selectedArtifacts = [NSArray array];
    }

  rootWritable = access([[selectedRoot stringByExpandingTildeInPath] fileSystemRepresentation], W_OK) == 0 ||
                 access([[[selectedRoot stringByExpandingTildeInPath] stringByDeletingLastPathComponent] fileSystemRepresentation], W_OK) == 0;

  if (manifest == nil)
    {
      ok = NO;
      status = @"error";
      summary = @"Release manifest validation failed.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"report_bug", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         errorMessage, @"message",
                                         nil]];
      *exitCode = 2;
    }
  else if ([scope isEqualToString: @"system"] && !isRoot)
    {
      ok = NO;
      status = @"error";
      summary = @"System-wide installation requires elevated privileges.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"rerun_with_elevated_privileges", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"Re-run this command with sudo.", @"message",
                                         nil]];
      *exitCode = 3;
    }
  else if (installRoot != nil && !rootWritable)
    {
      ok = NO;
      status = @"error";
      summary = @"The selected install root is not writable.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"rerun_with_elevated_privileges", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"Choose a writable install root or rerun with sufficient privileges.", @"message",
                                         nil]];
      *exitCode = 3;
    }
  else if ([selectedArtifacts count] == 0)
    {
      ok = NO;
      status = @"error";
      summary = @"No managed artifacts were found for this host.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"report_bug", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"No compatible managed artifacts are available for this host yet.", @"message",
                                         nil]];
      *exitCode = 4;
    }
  else if ([selectedArtifacts count] < 2)
    {
      status = @"warning";
      summary = @"Managed installation plan created, but the manifest does not yet contain a complete artifact set.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"report_bug", @"kind",
                                         [NSNumber numberWithInt: 2], @"priority",
                                         @"The current manifest is missing either the CLI or toolchain artifact for this host.", @"message",
                                         nil]];
      *exitCode = 0;
    }
  else
    {
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         execute ? @"apply_install_plan" : @"apply_install_plan", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"Proceed with artifact download, verification, and managed installation.", @"message",
                                         nil]];
      *exitCode = 0;
    }

  {
    NSMutableArray *artifactIds = [NSMutableArray array];
    NSUInteger i = 0;
    for (i = 0; i < [selectedArtifacts count]; i++)
      {
        [artifactIds addObject: [[selectedArtifacts objectAtIndex: i] objectForKey: @"id"]];
      }
    return [NSDictionary dictionaryWithObjectsAndKeys:
                          [NSNumber numberWithInt: 1], @"schema_version",
                          @"setup", @"command",
                          @"0.1.0-dev", @"cli_version",
                          [NSNumber numberWithBool: ok], @"ok",
                          status, @"status",
                          summary, @"summary",
                          [NSDictionary dictionaryWithObjectsAndKeys:
                                          [doctor objectForKey: @"status"], @"status",
                                          [doctor objectForKey: @"environment_classification"], @"environment_classification",
                                          [doctor objectForKey: @"summary"], @"summary",
                                          osName, @"os",
                                          nil], @"doctor",
                          [NSDictionary dictionaryWithObjectsAndKeys:
                                          scope, @"scope",
                                          selectedRoot, @"install_root",
                                          @"stable", @"channel",
                                          resolvedManifest, @"manifest_path",
                                          release ? [release objectForKey: @"version"] : [NSNull null], @"selected_release",
                                          artifactIds, @"selected_artifacts",
                                          [NSNumber numberWithBool: ([scope isEqualToString: @"system"] ? isRoot : YES)], @"system_privileges_ok",
                                          manifest ? [NSArray array] : [NSArray arrayWithObject: errorMessage], @"manifest_validation_errors",
                                          nil], @"plan",
                          actions, @"actions",
                          nil];
  }
}

- (BOOL)downloadURLString:(NSString *)urlString toPath:(NSString *)destination error:(NSString **)errorMessage
{
  NSURL *url = [NSURL URLWithString: urlString];
  NSData *data = nil;
  if (url == nil)
    {
      if ([[NSFileManager defaultManager] fileExistsAtPath: urlString])
        {
          return [[NSFileManager defaultManager] copyItemAtPath: urlString toPath: destination error: nil];
        }
      if (errorMessage != NULL)
        {
          *errorMessage = @"Artifact URL could not be resolved.";
        }
      return NO;
    }
  data = [NSData dataWithContentsOfURL: url];
  if (data == nil || [data writeToFile: destination atomically: YES] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Failed to download %@", urlString];
        }
      return NO;
    }
  return YES;
}

- (NSDictionary *)executeSetupForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *scope = @"user";
  NSString *manifestPath = nil;
  NSString *installRoot = nil;
  NSUInteger i = 0;
  NSDictionary *payload = nil;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--system"])
        {
          scope = @"system";
        }
      else if ([argument isEqualToString: @"--user"])
        {
          scope = @"user";
        }
      else if ([argument isEqualToString: @"--root"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"--root requires a value." data: nil];
            }
          installRoot = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--manifest"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"--manifest requires a value." data: nil];
            }
          manifestPath = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown setup option: %@", argument] data: nil];
        }
    }

  payload = [self buildSetupPayloadForScope: scope manifest: manifestPath installRoot: installRoot execute: YES exitCode: exitCode];
  if ([[payload objectForKey: @"ok"] boolValue] == NO || [[payload objectForKey: @"status"] isEqualToString: @"warning"])
    {
      return payload;
    }

  {
    NSDictionary *manifest = [self validateAndLoadManifest: [[payload objectForKey: @"plan"] objectForKey: @"manifest_path"] error: nil];
    NSDictionary *release = [self selectReleaseFromManifest: manifest];
    NSArray *artifacts = [self selectedArtifactsForRelease: release
                                                       os: [[[self buildDoctorPayloadWithInterface: @"bootstrap" manifestPath: [[payload objectForKey: @"plan"] objectForKey: @"manifest_path"]] objectForKey: @"environment"] objectForKey: @"os"]
                                                     arch: [[[self buildDoctorPayloadWithInterface: @"bootstrap" manifestPath: [[payload objectForKey: @"plan"] objectForKey: @"manifest_path"]] objectForKey: @"environment"] objectForKey: @"arch"]];
    NSString *installPath = [[[payload objectForKey: @"plan"] objectForKey: @"install_root"] stringByExpandingTildeInPath];
    NSString *staging = [installPath stringByAppendingPathComponent: @".staging/setup"];
    NSString *downloads = [staging stringByAppendingPathComponent: @"downloads"];
    NSString *extracts = [staging stringByAppendingPathComponent: @"extracts"];
    NSMutableArray *installedArtifacts = [NSMutableArray array];
    NSFileManager *manager = [NSFileManager defaultManager];
    NSString *errorMessage = nil;
    NSUInteger j = 0;

    [manager createDirectoryAtPath: downloads withIntermediateDirectories: YES attributes: nil error: nil];
    [manager createDirectoryAtPath: extracts withIntermediateDirectories: YES attributes: nil error: nil];
    [manager createDirectoryAtPath: installPath withIntermediateDirectories: YES attributes: nil error: nil];

    for (j = 0; j < [artifacts count]; j++)
      {
        NSDictionary *artifact = [artifacts objectAtIndex: j];
        NSString *sourcePath = nil;
        NSString *localCandidate = [[[payload objectForKey: @"plan"] objectForKey: @"manifest_path"] stringByDeletingLastPathComponent];
        NSString *downloadPath = [downloads stringByAppendingPathComponent: [[artifact objectForKey: @"url"] lastPathComponent]];
        NSString *extractPath = [extracts stringByAppendingPathComponent: [artifact objectForKey: @"id"]];
        NSString *copyError = nil;
        NSString *checksum = nil;
        NSString *sourceRoot = nil;

        if ([artifact objectForKey: @"filename"] != nil)
          {
            localCandidate = [localCandidate stringByAppendingPathComponent: [artifact objectForKey: @"filename"]];
          }
        else
          {
            localCandidate = [localCandidate stringByAppendingPathComponent: [[artifact objectForKey: @"url"] lastPathComponent]];
          }

        if ([manager fileExistsAtPath: localCandidate])
          {
            [manager removeItemAtPath: downloadPath error: nil];
            [manager copyItemAtPath: localCandidate toPath: downloadPath error: nil];
          }
        else if ([self downloadURLString: [artifact objectForKey: @"url"] toPath: downloadPath error: &errorMessage] == NO)
          {
            [manager removeItemAtPath: staging error: nil];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: errorMessage data: nil];
          }

        sourcePath = downloadPath;
        checksum = [self sha256ForFile: sourcePath];
        if (checksum == nil || [checksum isEqualToString: [artifact objectForKey: @"sha256"]] == NO)
          {
            [manager removeItemAtPath: staging error: nil];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: [NSString stringWithFormat: @"checksum mismatch for %@", [artifact objectForKey: @"id"]] data: nil];
          }

        if ([self extractArchive: sourcePath toDirectory: extractPath error: &errorMessage] == NO)
          {
            [manager removeItemAtPath: staging error: nil];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: errorMessage data: nil];
          }

        sourceRoot = [self singleChildDirectoryOrSelf: extractPath];
        if ([self copyTreeContentsFrom: sourceRoot to: installPath error: &copyError] == NO)
          {
            [manager removeItemAtPath: staging error: nil];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: copyError data: nil];
          }
        [installedArtifacts addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                        [artifact objectForKey: @"id"], @"artifact_id",
                                                        [NSArray arrayWithObject: installPath], @"paths",
                                                        nil]];
      }

    {
      NSString *stateDir = [installPath stringByAppendingPathComponent: @"state"];
      NSString *statePath = [stateDir stringByAppendingPathComponent: @"cli-state.json"];
      NSString *writeError = nil;
      [manager createDirectoryAtPath: stateDir withIntermediateDirectories: YES attributes: nil error: nil];
      [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                   [NSNumber numberWithInt: 1], @"schema_version",
                                                   [release objectForKey: @"version"], @"cli_version",
                                                   [release objectForKey: @"version"], @"toolchain_version",
                                                   [NSNumber numberWithInt: 1], @"packages_version",
                                                   @"setup", @"last_action",
                                                   @"healthy", @"status",
                                                   nil]
                            toPath: statePath
                             error: &writeError];
    }

    [manager removeItemAtPath: staging error: nil];
    *exitCode = 0;
    return [NSDictionary dictionaryWithObjectsAndKeys:
                          [NSNumber numberWithInt: 1], @"schema_version",
                          @"setup", @"command",
                          @"0.1.0-dev", @"cli_version",
                          [NSNumber numberWithBool: YES], @"ok",
                          @"ok", @"status",
                          @"Managed installation completed.", @"summary",
                          [payload objectForKey: @"doctor"], @"doctor",
                          [payload objectForKey: @"plan"], @"plan",
                          [NSArray arrayWithObjects:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"add_path", @"kind",
                                                     [NSNumber numberWithInt: 1], @"priority",
                                                     [NSString stringWithFormat: @"Add %@/bin and %@/System/Tools to PATH for future shells.", installPath, installPath], @"message",
                                                     nil],
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"delete_bootstrap", @"kind",
                                                     [NSNumber numberWithInt: 2], @"priority",
                                                     @"The bootstrap script is no longer required and may be deleted.", @"message",
                                                     nil],
                                     nil], @"actions",
                          [NSDictionary dictionaryWithObjectsAndKeys:
                                          installedArtifacts, @"installed_artifacts",
                                          [NSString stringWithFormat: @"export PATH=\"%@/bin:%@/System/Tools:$PATH\"", installPath, installPath], @"path_hint",
                                          installPath, @"install_root",
                                          nil], @"install",
                          nil];
  }
}

- (NSDictionary *)executeBuildForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *projectPath = ([arguments count] > 0 && [[[arguments objectAtIndex: 0] substringToIndex: 1] isEqualToString: @"-"] == NO) ? [arguments objectAtIndex: 0] : [[NSFileManager defaultManager] currentDirectoryPath];
  NSDictionary *project = [self detectProjectAtPath: projectPath];
  NSDictionary *result = nil;

  if ([[project objectForKey: @"supported"] boolValue] == NO)
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"build", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"The current directory is not a supported GNUstep Make project.", @"summary",
                            project, @"project",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  result = [self runCommand: [NSArray arrayWithObjects: @"make", nil]
            currentDirectory: [project objectForKey: @"project_dir"]];
  *exitCode = [[result objectForKey: @"exit_status"] intValue] == 0 ? 0 : 1;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"build", @"command",
                        [NSNumber numberWithBool: ([[result objectForKey: @"exit_status"] intValue] == 0)], @"ok",
                        ([[result objectForKey: @"exit_status"] intValue] == 0) ? @"ok" : @"error", @"status",
                        ([[result objectForKey: @"exit_status"] intValue] == 0) ? @"GNUstep Make build completed." : @"GNUstep Make build failed.", @"summary",
                        project, @"project",
                        @"gnustep-make", @"backend",
                        [NSArray arrayWithObjects: @"make", nil], @"invocation",
                        [result objectForKey: @"stdout"], @"stdout",
                        [result objectForKey: @"stderr"], @"stderr",
                        [result objectForKey: @"exit_status"], @"exit_status",
                        nil];
}

- (NSDictionary *)executeRunForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *projectPath = ([arguments count] > 0 && [[[arguments objectAtIndex: 0] substringToIndex: 1] isEqualToString: @"-"] == NO) ? [arguments objectAtIndex: 0] : [[NSFileManager defaultManager] currentDirectoryPath];
  NSDictionary *project = [self detectProjectAtPath: projectPath];
  NSArray *invocation = nil;
  NSString *backend = nil;
  NSDictionary *result = nil;

  if ([[project objectForKey: @"supported"] boolValue] == NO)
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"run", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"The current directory is not a supported GNUstep Make project.", @"summary",
                            project, @"project",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  if ([[project objectForKey: @"project_type"] isEqualToString: @"tool"])
    {
      invocation = [NSArray arrayWithObjects: [NSString stringWithFormat: @"./obj/%@", [project objectForKey: @"target_name"]], nil];
      backend = @"direct-exec";
    }
  else if ([[project objectForKey: @"project_type"] isEqualToString: @"app"])
    {
      invocation = [NSArray arrayWithObjects: @"openapp", [NSString stringWithFormat: @"%@.app", [project objectForKey: @"target_name"]], nil];
      backend = @"openapp";
    }
  else
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"run", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"The detected project type does not have a runnable target.", @"summary",
                            project, @"project",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  result = [self runCommand: invocation currentDirectory: [project objectForKey: @"project_dir"]];
  if ([[result objectForKey: @"launched"] boolValue] == NO)
    {
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"run", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Run target was not found. Build the project before running it.", @"summary",
                            project, @"project",
                            backend, @"backend",
                            invocation, @"invocation",
                            @"", @"stdout",
                            [result objectForKey: @"stderr"], @"stderr",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            nil];
    }

  *exitCode = [[result objectForKey: @"exit_status"] intValue] == 0 ? 0 : 1;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"run", @"command",
                        [NSNumber numberWithBool: ([[result objectForKey: @"exit_status"] intValue] == 0)], @"ok",
                        ([[result objectForKey: @"exit_status"] intValue] == 0) ? @"ok" : @"error", @"status",
                        ([[result objectForKey: @"exit_status"] intValue] == 0) ? @"Run completed." : @"Run failed.", @"summary",
                        project, @"project",
                        backend, @"backend",
                        invocation, @"invocation",
                        [result objectForKey: @"stdout"], @"stdout",
                        [result objectForKey: @"stderr"], @"stderr",
                        [result objectForKey: @"exit_status"], @"exit_status",
                        nil];
}

- (NSString *)managedGNUmakefileFlags
{
  return @"GNUSTEP_PREFIX := $(GNUSTEP_MAKEFILES)/../../..\n"
         @"GNUSTEP_LOCAL_LIB_DIR := $(GNUSTEP_PREFIX)/Local/Library/Libraries\n"
         @"GNUSTEP_SYSTEM_LIB_DIR := $(GNUSTEP_PREFIX)/System/Library/Libraries\n"
         @"GNUSTEP_RUNTIME_LIB_DIR := $(GNUSTEP_PREFIX)/lib\n"
         @"ADDITIONAL_OBJCFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include\n"
         @"ADDITIONAL_CPPFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include\n"
         @"ADDITIONAL_LDFLAGS += -L$(GNUSTEP_MAKEFILES)/../../../lib -L$(GNUSTEP_MAKEFILES)/../../../lib64\n"
         @"ADDITIONAL_LDFLAGS += -Wl,-rpath,$(GNUSTEP_LOCAL_LIB_DIR)\n"
         @"ADDITIONAL_LDFLAGS += -Wl,-rpath,$(GNUSTEP_SYSTEM_LIB_DIR)\n"
         @"ADDITIONAL_LDFLAGS += -Wl,-rpath,$(GNUSTEP_RUNTIME_LIB_DIR)\n"
         @"ADDITIONAL_TOOL_LIBS += -ldispatch -lBlocksRuntime\n\n";
}

- (BOOL)writeString:(NSString *)content toPath:(NSString *)path
{
  [[NSFileManager defaultManager] createDirectoryAtPath: [path stringByDeletingLastPathComponent]
                            withIntermediateDirectories: YES
                                             attributes: nil
                                                  error: nil];
  return [content writeToFile: path atomically: YES encoding: NSUTF8StringEncoding error: nil];
}

- (NSDictionary *)executeNewForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  BOOL listTemplates = NO;
  NSString *templateName = nil;
  NSString *destination = nil;
  NSString *name = nil;
  NSUInteger i = 0;
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *destPath = nil;
  NSMutableArray *createdFiles = [NSMutableArray array];

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--list-templates"])
        {
          listTemplates = YES;
        }
      else if ([argument isEqualToString: @"--name"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"new" ok: NO status: @"error" summary: @"--name requires a value." data: nil];
            }
          name = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"new" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown new option: %@", argument] data: nil];
        }
      else if (templateName == nil)
        {
          templateName = argument;
        }
      else if (destination == nil)
        {
          destination = argument;
        }
    }

  if (listTemplates)
    {
      *exitCode = 0;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"new", @"command",
                            [NSNumber numberWithBool: YES], @"ok",
                            @"ok", @"status",
                            [NSArray arrayWithObjects: @"gui-app", @"cli-tool", @"library", nil], @"templates",
                            nil];
    }

  if (templateName == nil || destination == nil)
    {
      *exitCode = 2;
      return [self payloadWithCommand: @"new" ok: NO status: @"error" summary: @"template and destination are required" data: nil];
    }

  destPath = [[destination stringByResolvingSymlinksInPath] length] > 0 ? [destination stringByResolvingSymlinksInPath] : destination;
  if ([manager fileExistsAtPath: destPath] && [[[manager contentsOfDirectoryAtPath: destPath error: nil] copy] autorelease] != nil &&
      [[manager contentsOfDirectoryAtPath: destPath error: nil] count] > 0)
    {
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"new", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Destination directory is not empty.", @"summary",
                            templateName, @"template",
                            destPath, @"destination",
                            [NSArray array], @"created_files",
                            nil];
    }

  if (name == nil)
    {
      name = [destPath lastPathComponent];
    }

  if ([templateName isEqualToString: @"cli-tool"])
    {
      [self writeString: [NSString stringWithFormat: @"include $(GNUSTEP_MAKEFILES)/common.make\n\nTOOL_NAME = %@\n%@_OBJC_FILES = main.m\n\n%@include $(GNUSTEP_MAKEFILES)/tool.make\n",
                           name, name, [self managedGNUmakefileFlags]]
              toPath: [destPath stringByAppendingPathComponent: @"GNUmakefile"]];
      [self writeString: @"#import <Foundation/Foundation.h>\n\nint main(void)\n{\n  printf(\"Hello from CLI tool\\n\");\n  return 0;\n}\n"
              toPath: [destPath stringByAppendingPathComponent: @"main.m"]];
      [self writeString: [NSString stringWithFormat: @"{\n  \"schema_version\": 1,\n  \"id\": \"org.example.%@\",\n  \"name\": \"%@\",\n  \"kind\": \"cli-tool\"\n}\n",
                           [name lowercaseString], name]
              toPath: [destPath stringByAppendingPathComponent: @"package.json"]];
      [createdFiles addObject: @"GNUmakefile"];
      [createdFiles addObject: @"main.m"];
      [createdFiles addObject: @"package.json"];
    }
  else if ([templateName isEqualToString: @"gui-app"])
    {
      [self writeString: [NSString stringWithFormat: @"include $(GNUSTEP_MAKEFILES)/common.make\n\nAPP_NAME = %@\n%@_OBJC_FILES = main.m AppController.m\n%@_RESOURCE_FILES = Resources/Info-gnustep.plist\n\n%@include $(GNUSTEP_MAKEFILES)/application.make\n",
                           name, name, name, [self managedGNUmakefileFlags]]
              toPath: [destPath stringByAppendingPathComponent: @"GNUmakefile"]];
      [self writeString: @"#import <AppKit/AppKit.h>\n\nint main(int argc, char **argv)\n{\n  return NSApplicationMain(argc, (const char **)argv);\n}\n"
              toPath: [destPath stringByAppendingPathComponent: @"main.m"]];
      [self writeString: @"#import <AppKit/AppKit.h>\n\n@interface AppController : NSObject\n@end\n\n@implementation AppController\n@end\n"
              toPath: [destPath stringByAppendingPathComponent: @"AppController.m"]];
      [self writeString: @"{\n}\n"
              toPath: [[destPath stringByAppendingPathComponent: @"Resources"] stringByAppendingPathComponent: @"Info-gnustep.plist"]];
      [self writeString: [NSString stringWithFormat: @"{\n  \"schema_version\": 1,\n  \"id\": \"org.example.%@\",\n  \"name\": \"%@\",\n  \"kind\": \"gui-app\"\n}\n",
                           [name lowercaseString], name]
              toPath: [destPath stringByAppendingPathComponent: @"package.json"]];
      [createdFiles addObject: @"GNUmakefile"];
      [createdFiles addObject: @"main.m"];
      [createdFiles addObject: @"AppController.m"];
      [createdFiles addObject: @"Resources/Info-gnustep.plist"];
      [createdFiles addObject: @"package.json"];
    }
  else if ([templateName isEqualToString: @"library"])
    {
      [self writeString: [NSString stringWithFormat: @"include $(GNUSTEP_MAKEFILES)/common.make\n\nLIBRARY_NAME = %@\n%@_OBJC_FILES = %@.m\n%@_HEADER_FILES = %@.h\n\n%@include $(GNUSTEP_MAKEFILES)/library.make\n",
                           name, name, name, name, name, [self managedGNUmakefileFlags]]
              toPath: [destPath stringByAppendingPathComponent: @"GNUmakefile"]];
      [self writeString: [NSString stringWithFormat: @"#import <Foundation/Foundation.h>\n\n@interface %@ : NSObject\n@end\n", name]
              toPath: [destPath stringByAppendingPathComponent: [NSString stringWithFormat: @"%@.h", name]]];
      [self writeString: [NSString stringWithFormat: @"#import \"%@.h\"\n\n@implementation %@\n@end\n", name, name]
              toPath: [destPath stringByAppendingPathComponent: [NSString stringWithFormat: @"%@.m", name]]];
      [self writeString: [NSString stringWithFormat: @"{\n  \"schema_version\": 1,\n  \"id\": \"org.example.%@\",\n  \"name\": \"%@\",\n  \"kind\": \"library\"\n}\n",
                           [name lowercaseString], name]
              toPath: [destPath stringByAppendingPathComponent: @"package.json"]];
      [createdFiles addObject: @"GNUmakefile"];
      [createdFiles addObject: [NSString stringWithFormat: @"%@.h", name]];
      [createdFiles addObject: [NSString stringWithFormat: @"%@.m", name]];
      [createdFiles addObject: @"package.json"];
    }
  else
    {
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"new", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            [NSString stringWithFormat: @"Unknown template: %@", templateName], @"summary",
                            templateName, @"template",
                            destPath, @"destination",
                            [NSArray array], @"created_files",
                            nil];
    }

  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"new", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Project template created.", @"summary",
                        templateName, @"template",
                        destPath, @"destination",
                        name, @"name",
                        createdFiles, @"created_files",
                        nil];
}

- (NSDictionary *)loadInstalledPackagesState:(NSString *)managedRoot
{
  NSString *statePath = [[managedRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"installed-packages.json"];
  NSDictionary *state = [self readJSONFile: statePath error: nil];
  if (state == nil)
    {
      return [NSDictionary dictionaryWithObject: [NSDictionary dictionary] forKey: @"packages"];
    }
  return state;
}

- (BOOL)saveInstalledPackagesState:(NSDictionary *)state managedRoot:(NSString *)managedRoot
{
  NSString *stateDir = [managedRoot stringByAppendingPathComponent: @"state"];
  NSString *statePath = [stateDir stringByAppendingPathComponent: @"installed-packages.json"];
  [[NSFileManager defaultManager] createDirectoryAtPath: stateDir withIntermediateDirectories: YES attributes: nil error: nil];
  return [self writeJSONStringObject: state toPath: statePath error: nil];
}

- (NSString *)resolvedArtifactPathFromURLString:(NSString *)urlString
{
  if ([urlString hasPrefix: @"file://"])
    {
      return [[[NSURL URLWithString: urlString] path] stringByResolvingSymlinksInPath];
    }
  return [urlString stringByResolvingSymlinksInPath];
}

- (NSDictionary *)executeInstallForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *root = [self defaultManagedRoot];
  NSString *manifestPath = nil;
  NSUInteger i = 0;
  NSDictionary *manifest = nil;
  NSMutableDictionary *state = nil;
  NSString *packageID = nil;
  NSDictionary *artifact = nil;
  NSString *artifactPath = nil;
  NSString *staging = nil;
  NSString *finalRoot = nil;
  NSString *extractError = nil;
  NSFileManager *manager = [NSFileManager defaultManager];
  NSMutableArray *installedFiles = [NSMutableArray array];
  NSDirectoryEnumerator *enumerator = nil;
  NSString *relative = nil;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--root"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: @"--root requires a value." data: nil];
            }
          root = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown install option: %@", argument] data: nil];
        }
      else
        {
          manifestPath = argument;
        }
    }

  if (manifestPath == nil)
    {
      *exitCode = 2;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: @"manifest_path is required." data: nil];
    }

  manifest = [self readJSONFile: manifestPath error: nil];
  if (manifest == nil)
    {
      *exitCode = 1;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: @"Package manifest not found." data: nil];
    }

  state = [[self loadInstalledPackagesState: root] mutableCopy];
  packageID = [manifest objectForKey: @"id"];
  if ([[state objectForKey: @"packages"] objectForKey: packageID] != nil)
    {
      *exitCode = 0;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"install", @"command",
                            [NSNumber numberWithBool: YES], @"ok",
                            @"ok", @"status",
                            @"Package is already installed.", @"summary",
                            packageID, @"package_id",
                            [[[state objectForKey: @"packages"] objectForKey: packageID] objectForKey: @"installed_files"], @"installed_files",
                            nil];
    }

  artifact = [[manifest objectForKey: @"artifacts"] count] > 0 ? [[manifest objectForKey: @"artifacts"] objectAtIndex: 0] : nil;
  artifactPath = [self resolvedArtifactPathFromURLString: [artifact objectForKey: @"url"]];
  if ([manager fileExistsAtPath: artifactPath] == NO)
    {
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"install", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Artifact not found.", @"summary",
                            packageID, @"package_id",
                            nil];
    }

  staging = [[[root stringByExpandingTildeInPath] stringByAppendingPathComponent: @".staging"] stringByAppendingPathComponent: packageID];
  finalRoot = [[[[root stringByExpandingTildeInPath] stringByAppendingPathComponent: @"packages"] stringByAppendingPathComponent: packageID] stringByResolvingSymlinksInPath];
  [manager removeItemAtPath: staging error: nil];
  [manager createDirectoryAtPath: staging withIntermediateDirectories: YES attributes: nil error: nil];
  if ([self extractArchive: artifactPath toDirectory: staging error: &extractError] == NO)
    {
      *exitCode = 1;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: extractError data: nil];
    }
  [manager removeItemAtPath: finalRoot error: nil];
  [manager createDirectoryAtPath: [finalRoot stringByDeletingLastPathComponent] withIntermediateDirectories: YES attributes: nil error: nil];
  [manager moveItemAtPath: staging toPath: finalRoot error: nil];

  enumerator = [manager enumeratorAtPath: finalRoot];
  while ((relative = [enumerator nextObject]) != nil)
    {
      NSString *fullPath = [finalRoot stringByAppendingPathComponent: relative];
      BOOL isDir = NO;
      [manager fileExistsAtPath: fullPath isDirectory: &isDir];
      if (!isDir)
        {
          [installedFiles addObject: [[[@"packages" stringByAppendingPathComponent: packageID] stringByAppendingPathComponent: relative] stringByStandardizingPath]];
        }
    }

  {
    NSMutableDictionary *packages = [[[state objectForKey: @"packages"] mutableCopy] autorelease];
    [packages setObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         [manifestPath stringByResolvingSymlinksInPath], @"manifest_path",
                                         finalRoot, @"install_root",
                                         installedFiles, @"installed_files",
                                         nil]
                 forKey: packageID];
    [state setObject: packages forKey: @"packages"];
  }
  [self saveInstalledPackagesState: state managedRoot: root];
  [state release];

  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"install", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Package installed.", @"summary",
                        packageID, @"package_id",
                        installedFiles, @"installed_files",
                        nil];
}

- (NSDictionary *)executeRemoveForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *root = [self defaultManagedRoot];
  NSString *packageID = nil;
  NSUInteger i = 0;
  NSMutableDictionary *state = nil;
  NSMutableDictionary *packages = nil;
  NSDictionary *record = nil;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--root"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"remove" ok: NO status: @"error" summary: @"--root requires a value." data: nil];
            }
          root = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"remove" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown remove option: %@", argument] data: nil];
        }
      else
        {
          packageID = argument;
        }
    }

  if (packageID == nil)
    {
      *exitCode = 2;
      return [self payloadWithCommand: @"remove" ok: NO status: @"error" summary: @"package_id is required." data: nil];
    }

  state = [[self loadInstalledPackagesState: root] mutableCopy];
  packages = [[[state objectForKey: @"packages"] mutableCopy] autorelease];
  record = [packages objectForKey: packageID];
  if (record == nil)
    {
      [state release];
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"remove", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Package is not installed.", @"summary",
                            packageID, @"package_id",
                            nil];
    }

  [[NSFileManager defaultManager] removeItemAtPath: [record objectForKey: @"install_root"] error: nil];
  [packages removeObjectForKey: packageID];
  [state setObject: packages forKey: @"packages"];
  [self saveInstalledPackagesState: state managedRoot: root];
  [state release];

  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"remove", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Package removed.", @"summary",
                        packageID, @"package_id",
                        nil];
}

- (NSString *)renderHumanForPayload:(NSDictionary *)payload
{
  NSString *command = [payload objectForKey: @"command"];
  if ([command isEqualToString: @"doctor"])
    {
      NSDictionary *environment = [payload objectForKey: @"environment"];
      NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
      NSMutableArray *lines = [NSMutableArray array];
      [lines addObject: [NSString stringWithFormat: @"doctor: %@", [payload objectForKey: @"summary"]]];
      [lines addObject: [NSString stringWithFormat: @"doctor: status=%@ classification=%@", [payload objectForKey: @"status"], [payload objectForKey: @"environment_classification"]]];
      [lines addObject: [NSString stringWithFormat: @"doctor: interface=%@ depth=%@", [payload objectForKey: @"interface"], [payload objectForKey: @"diagnostic_depth"]]];
      [lines addObject: [NSString stringWithFormat: @"doctor: host=%@/%@", [environment objectForKey: @"os"], [environment objectForKey: @"arch"]]];
      if ([[toolchain objectForKey: @"present"] boolValue])
        {
          [lines addObject: [NSString stringWithFormat: @"doctor: toolchain=%@ runtime=%@ abi=%@",
                              [toolchain objectForKey: @"compiler_family"],
                              [toolchain objectForKey: @"objc_runtime"],
                              [toolchain objectForKey: @"objc_abi"]]];
        }
      else
        {
          [lines addObject: @"doctor: toolchain=not detected"];
        }
      {
        NSUInteger i = 0;
        NSArray *actions = [payload objectForKey: @"actions"];
        for (i = 0; i < [actions count]; i++)
          {
            [lines addObject: [NSString stringWithFormat: @"next: %@", [[actions objectAtIndex: i] objectForKey: @"message"]]];
          }
      }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"setup"])
    {
      NSDictionary *plan = [payload objectForKey: @"plan"];
      NSMutableArray *lines = [NSMutableArray array];
      [lines addObject: [NSString stringWithFormat: @"setup: %@", [payload objectForKey: @"summary"]]];
      [lines addObject: [NSString stringWithFormat: @"setup: scope=%@ root=%@", [plan objectForKey: @"scope"], [plan objectForKey: @"install_root"]]];
      [lines addObject: [NSString stringWithFormat: @"setup: selected release=%@", [plan objectForKey: @"selected_release"]]];
      if ([payload objectForKey: @"install"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"setup: path hint=%@", [[payload objectForKey: @"install"] objectForKey: @"path_hint"]]];
        }
      {
        NSUInteger i = 0;
        NSArray *actions = [payload objectForKey: @"actions"];
        for (i = 0; i < [actions count]; i++)
          {
            [lines addObject: [NSString stringWithFormat: @"next: %@", [[actions objectAtIndex: i] objectForKey: @"message"]]];
          }
      }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"build"])
    {
      if ([[payload objectForKey: @"ok"] boolValue] == NO && [payload objectForKey: @"backend"] == [NSNull null])
        {
          return [payload objectForKey: @"summary"];
        }
      return [NSString stringWithFormat: @"build: %@\nbuild: backend=%@\nbuild: project_type=%@ target=%@\nbuild: invocation=make",
                [payload objectForKey: @"summary"],
                [payload objectForKey: @"backend"],
                [[payload objectForKey: @"project"] objectForKey: @"project_type"],
                [[payload objectForKey: @"project"] objectForKey: @"target_name"]];
    }
  if ([command isEqualToString: @"run"])
    {
      if ([[payload objectForKey: @"ok"] boolValue] == NO && [payload objectForKey: @"backend"] == [NSNull null])
        {
          return [payload objectForKey: @"summary"];
        }
      return [NSString stringWithFormat: @"run: %@\nrun: backend=%@\nrun: project_type=%@ target=%@\nrun: invocation=%@",
                [payload objectForKey: @"summary"],
                [payload objectForKey: @"backend"],
                [[payload objectForKey: @"project"] objectForKey: @"project_type"],
                [[payload objectForKey: @"project"] objectForKey: @"target_name"],
                [[payload objectForKey: @"invocation"] componentsJoinedByString: @" "]];
    }
  if ([command isEqualToString: @"new"])
    {
      if ([payload objectForKey: @"templates"] != nil)
        {
          return [[payload objectForKey: @"templates"] componentsJoinedByString: @"\n"];
        }
      return [payload objectForKey: @"summary"];
    }
  return [payload objectForKey: @"summary"];
}

- (int)runNativeCommandForContext:(GSCommandContext *)context
{
  NSDictionary *payload = nil;
  int exitCode = 0;
  NSString *command = [context command];

  if ([command isEqualToString: @"doctor"])
    {
      payload = [self executeDoctorForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"setup"])
    {
      payload = [self executeSetupForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"build"])
    {
      payload = [self executeBuildForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"run"])
    {
      payload = [self executeRunForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"new"])
    {
      payload = [self executeNewForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"install"])
    {
      payload = [self executeInstallForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"remove"])
    {
      payload = [self executeRemoveForContext: context exitCode: &exitCode];
    }
  else
    {
      payload = [self payloadWithCommand: command ok: NO status: @"error" summary: @"Unknown command." data: nil];
      exitCode = 2;
    }

  if ([context jsonOutput])
    {
      [self emitJSONPayload: payload];
    }
  else
    {
      printf("%s\n", [[self renderHumanForPayload: payload] UTF8String]);
    }
  return exitCode;
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

  return [self runNativeCommandForContext: context];
}

@end
