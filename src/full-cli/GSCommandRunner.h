#import <Foundation/Foundation.h>

@interface GSCommandRunner : NSObject

- (int)runWithArguments:(NSArray *)arguments;
- (NSArray *)knownCommands;

@end
