#import <Foundation/Foundation.h>

@interface GSCommandRunner : NSObject

- (int)runWithArguments:(NSArray<NSString *> *)arguments;
- (NSArray *)knownCommands;

@end
