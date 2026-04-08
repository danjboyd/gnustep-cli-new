#import <Foundation/Foundation.h>

@interface GSCommandContext : NSObject
{
  BOOL _jsonOutput;
  BOOL _verbose;
  BOOL _quiet;
  BOOL _yes;
  BOOL _showHelp;
  BOOL _showVersion;
  NSString *_command;
  NSArray *_commandArguments;
  NSString *_usageError;
}

+ (GSCommandContext *)contextWithArguments:(NSArray *)arguments;

- (BOOL)jsonOutput;
- (BOOL)verbose;
- (BOOL)quiet;
- (BOOL)yes;
- (BOOL)showHelp;
- (BOOL)showVersion;
- (NSString *)command;
- (NSArray *)commandArguments;
- (NSString *)usageError;

@end
