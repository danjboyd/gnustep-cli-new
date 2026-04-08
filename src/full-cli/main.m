#import <Foundation/Foundation.h>
#import "GSCommandRunner.h"

int main(int argc, char **argv)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];
  NSMutableArray *arguments = [NSMutableArray array];
  int i;
  for (i = 1; i < argc; i++)
    {
      [arguments addObject: [NSString stringWithUTF8String: argv[i]]];
    }
  GSCommandRunner *runner = [GSCommandRunner new];
  int status = [runner runWithArguments: arguments];
  [runner release];
  [pool drain];
  return status;
}

