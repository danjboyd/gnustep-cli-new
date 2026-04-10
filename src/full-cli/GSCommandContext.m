#import "GSCommandContext.h"

@implementation GSCommandContext

+ (GSCommandContext *)contextWithArguments:(NSArray *)arguments
{
  GSCommandContext *context = [[[GSCommandContext alloc] init] autorelease];
  NSMutableArray *remaining = [NSMutableArray array];
  NSEnumerator *enumerator = [arguments objectEnumerator];
  NSString *argument = nil;
  BOOL commandSeen = NO;

  while ((argument = [enumerator nextObject]) != nil)
    {
      if ([argument isEqualToString: @"--json"])
        {
          context->_jsonOutput = YES;
          continue;
        }
      if ([argument isEqualToString: @"--verbose"])
        {
          context->_verbose = YES;
          continue;
        }
      if ([argument isEqualToString: @"--quiet"])
        {
          context->_quiet = YES;
          continue;
        }
      if ([argument isEqualToString: @"--yes"])
        {
          context->_yes = YES;
          continue;
        }
      if ([argument isEqualToString: @"--help"])
        {
          context->_showHelp = YES;
          continue;
        }
      if ([argument isEqualToString: @"--version"])
        {
          context->_showVersion = YES;
          continue;
        }
      if (commandSeen == NO && [argument hasPrefix: @"--"])
        {
          context->_usageError = [NSString stringWithFormat: @"Unknown global option: %@", argument];
          return context;
        }

      if (context->_command == nil)
        {
          context->_command = [argument copy];
          commandSeen = YES;
        }
      else
        {
          [remaining addObject: argument];
          commandSeen = YES;
        }
    }

  context->_commandArguments = [remaining copy];
  return context;
}

- (void)dealloc
{
  [_command release];
  [_commandArguments release];
  [_usageError release];
  [super dealloc];
}

- (BOOL)jsonOutput
{
  return _jsonOutput;
}

- (BOOL)verbose
{
  return _verbose;
}

- (BOOL)quiet
{
  return _quiet;
}

- (BOOL)yes
{
  return _yes;
}

- (BOOL)showHelp
{
  return _showHelp;
}

- (BOOL)showVersion
{
  return _showVersion;
}

- (NSString *)command
{
  return _command;
}

- (NSArray *)commandArguments
{
  return _commandArguments;
}

- (NSString *)usageError
{
  return _usageError;
}

@end
